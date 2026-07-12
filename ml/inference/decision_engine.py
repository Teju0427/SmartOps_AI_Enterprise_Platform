"""
Phase 4 — AI Decision Engine.

Combines outputs from every Phase 3 model (health, failure, RUL, price,
demand, customer intelligence) into prioritized, human-readable business
recommendations - e.g. "Schedule maintenance for Compressor X", "Replace
Excavator Y", "Relocate Crane Z to Bengaluru".

Run:
    docker compose exec backend python ml/inference/decision_engine.py
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.equipment import Equipment  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.decision import (  # noqa: E402
    DecisionRecommendation, RecommendationCategory, RecommendationStatus,
)

from inference.predict_failure import FailurePredictor  # noqa: E402
from inference.predict_health import HealthPredictor  # noqa: E402
from inference.predict_rul import RULPredictor  # noqa: E402
from inference.predict_demand import DemandPredictor  # noqa: E402
from inference.predict_customer import CustomerIntelligencePredictor  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("decision_engine")


def _sensor_payload(eq: Equipment) -> dict:
    if eq.base_daily_rate >= 900:
        ai4i_type = "H"
    elif eq.base_daily_rate >= 350:
        ai4i_type = "M"
    else:
        ai4i_type = "L"
    return {
        "type": ai4i_type,
        "air_temperature_k": eq.air_temperature_k or 298.0,
        "process_temperature_k": eq.process_temperature_k or 308.0,
        "rotational_speed_rpm": eq.rotational_speed_rpm or 1500.0,
        "torque_nm": eq.torque_nm or 40.0,
        "tool_wear_min": eq.tool_wear_min or 0.0,
    }


class DecisionEngine:
    def __init__(self) -> None:
        self.failure_predictor = FailurePredictor()
        self.health_predictor = HealthPredictor()
        self.rul_predictor = RULPredictor()
        self.demand_predictor = DemandPredictor()
        self.customer_predictor = CustomerIntelligencePredictor()

    def evaluate_equipment(self, eq: Equipment, region_inventory: dict, region_demand_share: dict) -> list[dict]:
        payload = _sensor_payload(eq)
        failure = self.failure_predictor.predict(payload)
        health = self.health_predictor.predict(payload)
        rul = self.rul_predictor.predict(payload)

        recs: list[dict] = []

        if failure["risk_tier"] == "high" or rul["remaining_useful_life_days"] <= 7:
            urgency_days = max(1, int(rul["remaining_useful_life_days"]))
            recs.append({
                "category": RecommendationCategory.MAINTENANCE,
                "equipment_id": eq.id,
                "title": f"Schedule maintenance for {eq.name}",
                "summary": f"Schedule maintenance within {urgency_days} days",
                "reasoning": (
                    f"Failure probability {failure['failure_probability']:.1%} ({failure['risk_tier']} risk), "
                    f"estimated {rul['remaining_useful_life_days']:.1f} days remaining useful life "
                    f"(range {rul['confidence_interval_lower_days']:.1f}-{rul['confidence_interval_upper_days']:.1f} days). "
                    f"Current health score {health['health_score']}/100 ({health['status']})."
                ),
                "estimated_impact_metric": "downtime_avoidance",
                "estimated_impact_value": round(eq.base_daily_rate * 5, 2),
                "priority_score": min(100, 60 + failure["failure_probability"] * 40),
                "confidence_score": failure["failure_probability"] if failure["risk_tier"] == "high" else 0.75,
            })
        elif failure["risk_tier"] == "medium":
            recs.append({
                "category": RecommendationCategory.MAINTENANCE,
                "equipment_id": eq.id,
                "title": f"Plan preventive maintenance for {eq.name}",
                "summary": f"Plan preventive maintenance within {int(rul['remaining_useful_life_days'])} days",
                "reasoning": (
                    f"Medium failure risk ({failure['failure_probability']:.1%}); health {health['health_score']}/100. "
                    "Proactive scheduling avoids unplanned downtime during an active rental."
                ),
                "estimated_impact_metric": "downtime_avoidance",
                "estimated_impact_value": round(eq.base_daily_rate * 2, 2),
                "priority_score": 45,
                "confidence_score": 0.65,
            })

        equipment_age_years = ((datetime.now(timezone.utc).date() - eq.purchase_date).days / 365) if eq.purchase_date else 0
        if health["status"] == "critical" and equipment_age_years >= 4 and rul["remaining_useful_life_days"] < 5:
            recs.append({
                "category": RecommendationCategory.FLEET_REPLACEMENT,
                "equipment_id": eq.id,
                "title": f"Replace {eq.name}",
                "summary": f"Replace {eq.name} next maintenance cycle",
                "reasoning": (
                    f"{equipment_age_years:.1f} years old, critical health ({health['health_score']}/100), "
                    f"only {rul['remaining_useful_life_days']:.1f} days RUL remaining. Repeated repair costs are "
                    "likely to exceed replacement value at this point in the asset's lifecycle."
                ),
                "estimated_impact_metric": "cost_avoidance",
                "estimated_impact_value": round(eq.purchase_cost * 0.15, 2) if eq.purchase_cost else None,
                "priority_score": 80,
                "confidence_score": 0.7,
            })

        eq_type = eq.equipment_type.value if hasattr(eq.equipment_type, "value") else eq.equipment_type
        current_region_count = region_inventory.get(eq.current_region, {}).get(eq_type, 0)
        demand_share_here = region_demand_share.get(eq.current_region, 0.1)

        better_region = None
        best_gap = 0
        for region, share in region_demand_share.items():
            if region == eq.current_region:
                continue
            count_there = region_inventory.get(region, {}).get(eq_type, 0)
            gap = (share - demand_share_here) - (count_there - current_region_count) * 0.02
            if gap > best_gap and share > demand_share_here * 1.3 and count_there < current_region_count:
                best_gap = gap
                better_region = region

        if better_region and health["status"] != "critical":
            recs.append({
                "category": RecommendationCategory.INVENTORY_RELOCATION,
                "equipment_id": eq.id,
                "title": f"Relocate {eq.name} to {better_region}",
                "summary": f"Move {eq.name} from {eq.current_region} to {better_region}",
                "reasoning": (
                    f"{better_region} shows {region_demand_share.get(better_region, 0):.1%} of national demand share "
                    f"vs {eq.current_region}'s {demand_share_here:.1%}, with fewer {eq_type} units currently stationed there "
                    f"({region_inventory.get(better_region, {}).get(eq_type, 0)} vs {current_region_count})."
                ),
                "estimated_impact_metric": "utilization_increase",
                "estimated_impact_value": round(eq.base_daily_rate * 10, 2),
                "priority_score": 35,
                "confidence_score": 0.6,
            })

        return recs

    def evaluate_customer(self, customer: Customer) -> list[dict]:
        if customer.total_rentals < 1:
            return []

        payload = {
            "industry": customer.industry.value if hasattr(customer.industry, "value") else customer.industry,
            "region": customer.region,
            "credit_limit": customer.credit_limit,
            "tenure_days": (datetime.now(timezone.utc).date() - customer.onboarded_date).days,
            "total_rentals": customer.total_rentals,
            "avg_discount_pct": 5.0,
            "avg_duration_days": 14.0,
        }
        result = self.customer_predictor.predict(payload)

        recs = []
        if result["late_payment_risk_tier"] == "high" and result["predicted_lifetime_value"] > 50000:
            recs.append({
                "category": RecommendationCategory.CUSTOMER_RETENTION,
                "customer_id": customer.id,
                "title": f"Proactive outreach: {customer.company_name}",
                "summary": f"Reach out to {customer.company_name} before renewal - elevated payment risk on high-value account",
                "reasoning": (
                    f"Predicted lifetime value ${result['predicted_lifetime_value']:,.0f} puts this customer in the "
                    f"top value tier, but late-payment risk is {result['late_payment_risk_probability']:.1%} "
                    f"({result['late_payment_risk_tier']}). Recommended discount if renewing: "
                    f"{result['recommended_discount_pct']}%."
                ),
                "estimated_impact_metric": "revenue_retention",
                "estimated_impact_value": round(result["predicted_lifetime_value"] * 0.3, 2),
                "priority_score": 55,
                "confidence_score": 0.6,
            })
        return recs

    @staticmethod
    def build_region_inventory(db) -> dict:
        rows = db.query(Equipment.current_region, Equipment.equipment_type, func.count(Equipment.id)) \
            .group_by(Equipment.current_region, Equipment.equipment_type).all()
        inventory: dict = {}
        for region, eq_type, count in rows:
            eq_type_str = eq_type.value if hasattr(eq_type, "value") else eq_type
            inventory.setdefault(region, {})[eq_type_str] = count
        return inventory

    def build_region_demand_share(self) -> dict:
        return self.demand_predictor.region_share


def persist_recommendations(db, recs: list[dict]) -> int:
    count = 0
    for r in recs:
        contributing = json.dumps([str(uuid.uuid4())])
        db.add(DecisionRecommendation(
            created_at=datetime.now(timezone.utc),
            category=r["category"],
            status=RecommendationStatus.PENDING,
            equipment_id=r.get("equipment_id"),
            customer_id=r.get("customer_id"),
            title=r["title"],
            summary=r["summary"],
            detailed_reasoning=r["reasoning"],
            contributing_prediction_ids=contributing,
            estimated_impact_value=r.get("estimated_impact_value"),
            estimated_impact_metric=r.get("estimated_impact_metric"),
            priority_score=r["priority_score"],
            confidence_score=r["confidence_score"],
        ))
        count += 1
    db.commit()
    return count


def run(persist: bool = True) -> list[dict]:
    engine = DecisionEngine()
    db = SessionLocal()
    all_recs: list[dict] = []
    try:
        region_inventory = engine.build_region_inventory(db)
        region_demand_share = engine.build_region_demand_share()

        equipment_list = db.query(Equipment).filter(Equipment.is_deleted.is_(False)).all()
        logger.info("Evaluating %d equipment records...", len(equipment_list))
        for eq in equipment_list:
            all_recs.extend(engine.evaluate_equipment(eq, region_inventory, region_demand_share))

        customers = db.query(Customer).filter(Customer.is_deleted.is_(False)).all()
        logger.info("Evaluating %d customer records...", len(customers))
        for customer in customers:
            all_recs.extend(engine.evaluate_customer(customer))

        all_recs.sort(key=lambda r: r["priority_score"], reverse=True)
        logger.info("Generated %d recommendations.", len(all_recs))

        by_category: dict = {}
        for r in all_recs:
            cat = r["category"].value if hasattr(r["category"], "value") else r["category"]
            by_category[cat] = by_category.get(cat, 0) + 1
        logger.info("By category: %s", json.dumps(by_category, indent=2))

        if persist:
            n = persist_recommendations(db, all_recs)
            logger.info("Persisted %d DecisionRecommendation rows.", n)

        logger.info("Top 5 recommendations:")
        for r in all_recs[:5]:
            logger.info("  [%.0f] %s - %s", r["priority_score"], r["title"], r["summary"])

        return all_recs
    finally:
        db.close()


if __name__ == "__main__":
    run(persist=True)
