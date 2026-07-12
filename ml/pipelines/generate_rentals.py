"""
ETL Stage 3b — synthetic rental transaction history.

Generates realistic rental contracts against the sampled equipment fleet
and customer base. Pricing, duration, and discount patterns are driven by
equipment type, region, customer industry, and (importantly) each
machine's AI4I-derived health signal — healthier machines rent more
often and at a smaller discount; degraded machines rent less and are
more likely to see a late return / overdue status, mirroring how
equipment condition actually affects utilization in the real business.

Run:
    python ml/pipelines/generate_rentals.py
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("etl.generate_rentals")

SEED = 42
HISTORY_DAYS = 540  # ~18 months of rental history
random.seed(SEED)
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parents[2] / "datasets" / "processed"
FLEET_PATH = BASE_DIR / "equipment_fleet.parquet"
CUSTOMERS_PATH = BASE_DIR / "customers.parquet"
OUT_RENTALS = BASE_DIR / "rentals.parquet"
OUT_MAINTENANCE = BASE_DIR / "maintenance.parquet"

RENTAL_STATUSES_PAST = ["returned", "cancelled"]
RENTAL_STATUS_WEIGHTS_PAST = [0.93, 0.07]


def _competitor_price(base_rate: float) -> float:
    """Competitor pricing typically hovers within +/-15% of a fair market rate."""
    return round(base_rate * np.random.uniform(0.85, 1.15), 2)


# Industrial equipment rental demand in India genuinely follows a
# seasonal pattern: construction/infrastructure activity picks up in the
# post-monsoon and dry season (Oct-Jun) and slows during the monsoon
# (Jul-Sep) when outdoor construction work is disrupted. Embedding this
# real seasonal structure (rather than leaving rental timing purely
# random) gives the Phase 3 demand forecasting model genuine, learnable
# signal instead of pure noise.
SEASON_WEIGHT_BY_MONTH = {
    1: 1.3, 2: 1.3, 3: 1.35, 4: 1.25, 5: 1.15, 6: 0.75,
    7: 0.55, 8: 0.55, 9: 0.7, 10: 1.2, 11: 1.35, 12: 1.35,
}


def _seasonal_sample_days(w_start: int, w_end: int, n_rentals: int, history_days: int) -> np.ndarray:
    """Sample n_rentals day-offsets from [w_start, w_end], biased toward
    higher-season months per SEASON_WEIGHT_BY_MONTH, via weighted sampling
    without replacement from an oversampled candidate pool."""
    n_candidates = max(n_rentals * 4, 12)
    candidates = np.linspace(w_start, w_end, n_candidates)
    candidates += np.random.uniform(-3, 3, size=n_candidates)
    candidates = np.clip(candidates, 0, history_days - 3)

    months = np.array([
        (date.today() - timedelta(days=int(history_days - d))).month for d in candidates
    ])
    weights = np.array([SEASON_WEIGHT_BY_MONTH[m] for m in months], dtype=float)
    weights = weights / weights.sum()

    n_select = min(n_rentals, n_candidates)
    chosen_idx = np.random.choice(n_candidates, size=n_select, replace=False, p=weights)
    return np.sort(candidates[chosen_idx]).astype(int)


def generate_rentals(fleet: pd.DataFrame, customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rental_rows = []
    maintenance_rows = []
    rental_counter = 1000

    for _, eq in fleet.iterrows():
        health = eq["heuristic_health_score"]
        # Healthier equipment rents more often (higher utilization);
        # degraded equipment sits idle / goes to maintenance more.
        n_rentals = int(np.clip(np.random.poisson(lam=max(health / 100 * 7, 0.5)), 0, 14))

        # Same-region customers rent equipment more often than cross-region
        same_region_customers = customers[customers["region"] == eq["current_region"]]
        pool = same_region_customers if len(same_region_customers) >= 3 else customers

        # Spread rentals evenly across the FULL history window rather than
        # consuming sequentially from day 0 - the previous sequential-cursor
        # approach caused rentals to cluster in early months and left the
        # most recent weeks almost empty, which is a synthetic-data
        # artifact (not realistic business behavior) and breaks any
        # forecasting model trained on the resulting time series.
        if n_rentals > 0:
            w_start = random.randint(0, 100)
            w_end = max(w_start + 10, (HISTORY_DAYS - 5) - int(np.random.exponential(scale=25)))
            start_days = _seasonal_sample_days(w_start, w_end, n_rentals, HISTORY_DAYS)
        else:
            start_days = []

        for start_day in start_days:
            customer = pool.sample(1).iloc[0]

            duration = int(np.clip(np.random.exponential(scale=14), 2, 120))
            start_date = date.today() - timedelta(days=HISTORY_DAYS - int(start_day))
            end_planned = start_date + timedelta(days=duration)

            base_rate = eq["base_daily_rate"]
            competitor_price = _competitor_price(base_rate)

            # AI-suggested price heuristic (a real trained pricing model
            # arrives in Phase 4 — this seeds historical "suggested vs
            # actual" pairs the model will later be validated against):
            # nudge toward competitor price, adjusted for equipment health
            # and duration-based discounting.
            health_adjustment = 1 + ((health - 85) / 100) * 0.08
            duration_discount = 1 - min(duration / 90, 1) * 0.12
            ai_suggested_price = round(
                ((base_rate * 0.5) + (competitor_price * 0.5)) * health_adjustment * duration_discount, 2
            )
            ai_confidence = round(np.random.uniform(0.78, 0.97), 3)

            discount_pct = round(max(0, np.random.normal(loc=5, scale=4)), 2)
            final_rate = round(ai_suggested_price * (1 - discount_pct / 100), 2)

            status = np.random.choice(RENTAL_STATUSES_PAST, p=RENTAL_STATUS_WEIGHTS_PAST)
            is_cancelled = status == "cancelled"

            end_actual = None
            total_revenue = total_cost = total_profit = None
            payment_due = payment_received = None
            is_late_payment = False

            if not is_cancelled:
                # Degraded equipment more likely to be returned late
                late_prob = np.clip((90 - health) / 200, 0.02, 0.35)
                overrun_days = int(np.random.exponential(scale=3)) if np.random.random() < late_prob else 0
                end_actual = end_planned + timedelta(days=overrun_days)

                total_revenue = round(final_rate * duration, 2)
                cost_ratio = np.random.uniform(0.45, 0.65)  # equipment cost + logistics + labor
                total_cost = round(total_revenue * cost_ratio, 2)
                total_profit = round(total_revenue - total_cost, 2)

                payment_due = end_actual + timedelta(days=30)
                pay_delay_prob = np.clip((90 - health) / 250, 0.03, 0.30)
                pay_overrun = int(np.random.exponential(scale=10)) if np.random.random() < pay_delay_prob else 0
                payment_received = payment_due + timedelta(days=pay_overrun) if np.random.random() < 0.97 else None
                is_late_payment = pay_overrun > 5

            rental_counter += 1
            rental_rows.append({
                "rental_id": str(uuid.uuid4()),
                "rental_number": f"RNT-{rental_counter}",
                "equipment_id": eq["equipment_id"],
                "customer_id": customer["customer_id"],
                "status": "cancelled" if is_cancelled else ("overdue" if end_actual and end_actual > end_planned + timedelta(days=2) and payment_received is None else "returned"),
                "start_date": start_date,
                "end_date_planned": end_planned,
                "end_date_actual": end_actual,
                "duration_days_planned": duration,
                "region": eq["current_region"],
                "market_competitor_price": competitor_price,
                "ai_suggested_price": ai_suggested_price,
                "ai_price_confidence": ai_confidence,
                "quoted_daily_rate": ai_suggested_price,
                "final_daily_rate": None if is_cancelled else final_rate,
                "discount_applied_pct": discount_pct,
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "payment_due_date": payment_due,
                "payment_received_date": payment_received,
                "is_late_payment": is_late_payment,
            })

            # (rental spacing is now handled by the anchor-based sampling above)

        # ---- Maintenance records, driven by the actual AI4I failure flags ----
        failure_map = {
            "TWF": ("Tool Wear Failure", "corrective"),
            "HDF": ("Heat Dissipation Failure", "corrective"),
            "PWF": ("Power Failure", "emergency"),
            "OSF": ("Overstrain Failure", "emergency"),
            "RNF": ("Random Failure", "corrective"),
        }
        for flag, (label, mtype) in failure_map.items():
            if eq.get(flag, 0) == 1:
                event_date = date.today() - timedelta(days=random.randint(5, HISTORY_DAYS))
                cost = round(np.random.uniform(15000, 180000), 2)  # INR-scale repair cost
                maintenance_rows.append({
                    "maintenance_id": str(uuid.uuid4()),
                    "equipment_id": eq["equipment_id"],
                    "maintenance_type": mtype,
                    "status": "completed",
                    "recommended_date": event_date - timedelta(days=3),
                    "ai_estimated_cost": round(cost * np.random.uniform(0.85, 1.1), 2),
                    "ai_confidence": round(np.random.uniform(0.7, 0.95), 3),
                    "ai_reasoning": f"Elevated risk signature consistent with {label} pattern detected in sensor telemetry.",
                    "scheduled_date": event_date - timedelta(days=1),
                    "completed_date": event_date,
                    "actual_cost": cost,
                    "technician_notes": f"{label} confirmed on inspection; component replaced.",
                    "parts_replaced": label.split()[0].lower() + "_assembly",
                    "downtime_hours": round(np.random.uniform(4, 72), 1),
                })

        # Routine preventive maintenance (independent of failure flags) -
        # every fleet asset gets periodic scheduled maintenance regardless
        # of failure history, matching real fleet operating practice.
        n_preventive = random.randint(1, 4)
        for _ in range(n_preventive):
            event_date = date.today() - timedelta(days=random.randint(1, HISTORY_DAYS))
            is_future = event_date > date.today()
            maintenance_rows.append({
                "maintenance_id": str(uuid.uuid4()),
                "equipment_id": eq["equipment_id"],
                "maintenance_type": "preventive",
                "status": "scheduled" if is_future else "completed",
                "recommended_date": event_date,
                "ai_estimated_cost": round(np.random.uniform(3000, 25000), 2),
                "ai_confidence": round(np.random.uniform(0.75, 0.98), 3),
                "ai_reasoning": "Routine preventive maintenance interval reached based on operating hours.",
                "scheduled_date": event_date,
                "completed_date": None if is_future else event_date,
                "actual_cost": None if is_future else round(np.random.uniform(3000, 25000), 2),
                "technician_notes": None if is_future else "Standard service completed, no anomalies found.",
                "parts_replaced": None if is_future else "filters_and_lubricant",
                "downtime_hours": None if is_future else round(np.random.uniform(1, 8), 1),
            })

    rentals_df = pd.DataFrame(rental_rows)
    maintenance_df = pd.DataFrame(maintenance_rows)
    return rentals_df, maintenance_df


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    fleet = pd.read_parquet(FLEET_PATH)
    customers = pd.read_parquet(CUSTOMERS_PATH)

    rentals_df, maintenance_df = generate_rentals(fleet, customers)

    rentals_df.to_parquet(OUT_RENTALS, index=False)
    maintenance_df.to_parquet(OUT_MAINTENANCE, index=False)

    logger.info("Wrote %d rentals to %s", len(rentals_df), OUT_RENTALS)
    logger.info("Wrote %d maintenance records to %s", len(maintenance_df), OUT_MAINTENANCE)
    logger.info("Rental status breakdown:\n%s", rentals_df["status"].value_counts().to_string())
    logger.info("Maintenance type breakdown:\n%s", maintenance_df["maintenance_type"].value_counts().to_string())
    logger.info("Total historical revenue: %.2f", rentals_df["total_revenue"].sum(skipna=True))

    return rentals_df, maintenance_df


if __name__ == "__main__":
    run()
