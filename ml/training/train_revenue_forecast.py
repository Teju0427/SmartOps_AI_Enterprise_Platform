"""Phase 3 — Revenue Forecasting. Weekly national revenue/profit/utilization
via GradientBoostingRegressor, same lag+seasonal design as demand model."""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
import joblib, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.revenue_forecast")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
FEATURE_COLUMNS = ["lag_1", "lag_2", "lag_4", "rolling_mean_4", "week_of_year_sin", "week_of_year_cos"]
SEED = 42


def build_weekly_series() -> pd.DataFrame:
    rentals = pd.read_parquet(DATA_DIR / "rentals.parquet")
    rentals = rentals.dropna(subset=["total_revenue"])
    rentals["start_date"] = pd.to_datetime(rentals["start_date"])
    full_weeks = pd.date_range(
        rentals["start_date"].min().to_period("W").start_time,
        rentals["start_date"].max().to_period("W").start_time, freq="W-MON")
    weekly = rentals.set_index("start_date").resample("W-MON").agg(
        revenue=("total_revenue", "sum"), profit=("total_profit", "sum"), n_rentals=("total_revenue", "count"),
    ).reindex(full_weeks, fill_value=0)
    df = weekly.reset_index().rename(columns={"index": "week_start"})
    df["utilization_proxy"] = (df["n_rentals"] / df["n_rentals"].rolling(8, min_periods=1).max().replace(0, 1)).clip(0, 1)
    return df


def engineer(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    df = df.sort_values("week_start").copy()
    for lag in [1, 2, 4]:
        df[f"lag_{lag}"] = df[target_col].shift(lag)
    df["rolling_mean_4"] = df[target_col].shift(1).rolling(4).mean()
    woy = df["week_start"].dt.isocalendar().week.astype(int)
    df["week_of_year_sin"] = np.sin(2 * np.pi * woy / 52)
    df["week_of_year_cos"] = np.cos(2 * np.pi * woy / 52)
    return df.dropna(subset=[f"lag_{l}" for l in [1, 2, 4]] + ["rolling_mean_4"]).reset_index(drop=True)


def train_one(df: pd.DataFrame, target_col: str) -> tuple[GradientBoostingRegressor, dict]:
    featured = engineer(df, target_col)
    split = int(len(featured) * 0.8)
    train, test = featured.iloc[:split], featured.iloc[split:]
    X_train, y_train = train[FEATURE_COLUMNS], train[target_col]
    X_test, y_test = test[FEATURE_COLUMNS], test[target_col]

    model = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05,
                                       subsample=0.85, random_state=SEED)
    model.fit(X_train, y_train)
    pred = np.clip(model.predict(X_test), 0, None)
    naive_mae = mean_absolute_error(y_test, test["lag_1"])
    metrics = {
        "mae": round(float(mean_absolute_error(y_test, pred)), 2),
        "r2_score": round(float(r2_score(y_test, pred)), 4),
        "naive_baseline_mae": round(float(naive_mae), 2),
        "train_set_size": int(len(train)), "test_set_size": int(len(test)),
    }
    logger.info("%s metrics: %s", target_col, json.dumps(metrics))
    return model, metrics, featured


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    weekly_df = build_weekly_series()
    logger.info("Weekly series: %d weeks", len(weekly_df))

    revenue_model, revenue_metrics, featured = train_one(weekly_df, "revenue")
    profit_model, profit_metrics, _ = train_one(weekly_df, "profit")

    joblib.dump(revenue_model, ARTIFACTS_DIR / "revenue_model.joblib")
    joblib.dump(profit_model, ARTIFACTS_DIR / "profit_model.joblib")

    latest = featured.sort_values("week_start").tail(1).iloc[0]
    profit_featured = engineer(weekly_df, "profit").sort_values("week_start").tail(1).iloc[0]
    util_latest = weekly_df.sort_values("week_start").tail(1).iloc[0]

    meta = {
        "model_name": "revenue_forecast", "model_version": "gbr-revenue-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "revenue_metrics": revenue_metrics, "profit_metrics": profit_metrics,
        "granularity_trained_on": "weekly_national",
        "latest_revenue_state": {"week_start": str(latest["week_start"].date()), "lag_1": float(latest["lag_1"]),
                                  "lag_2": float(latest["lag_2"]), "lag_4": float(latest["lag_4"]),
                                  "rolling_mean_4": float(latest["rolling_mean_4"])},
        "latest_profit_state": {"lag_1": float(profit_featured["lag_1"]), "lag_2": float(profit_featured["lag_2"]),
                                 "lag_4": float(profit_featured["lag_4"]), "rolling_mean_4": float(profit_featured["rolling_mean_4"])},
        "latest_utilization_proxy": float(util_latest["utilization_proxy"]),
        "historical_avg_margin": float((pd.read_parquet(DATA_DIR / "rentals.parquet").dropna(subset=["total_revenue"])
                                         .assign(margin=lambda d: d["total_profit"] / d["total_revenue"])["margin"]).mean()),
    }
    with open(ARTIFACTS_DIR / "revenue_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved revenue + profit models.")


if __name__ == "__main__":
    run()
