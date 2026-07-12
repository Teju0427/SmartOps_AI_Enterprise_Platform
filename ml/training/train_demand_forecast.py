"""
Phase 3 — Demand Forecasting.

Design note (revised): an earlier version of this model attempted to
forecast weekly demand independently PER REGION. With ~2,600 total
historical rentals split across 10 regions and ~18 months, each
region's individual weekly series is too sparse and noisy to model
reliably (holdout R^2 was negative — worse than predicting the mean).

This is the same problem real demand-planning systems hit with sparse
regional data, and the standard fix is the one used here: forecast the
strong, smooth NATIONAL weekly total with LightGBM (lag + rolling +
seasonal features), then disaggregate that total across regions using
each region's stable historical share of demand. This produces far more
reliable regional numbers than fitting 10 separate sparse models, at the
cost of not capturing region-specific demand shocks independently -  a
documented, defensible tradeoff given the available data volume.

Outputs (to ml/artifacts/):
    demand_model.joblib        - national weekly-total forecaster
    demand_model_meta.json     - includes each region's historical share

Run:
    python ml/training/train_demand_forecast.py
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.demand_forecast")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"

FEATURE_COLUMNS = ["lag_1", "lag_2", "lag_4", "rolling_mean_4", "week_of_year_sin", "week_of_year_cos", "week_index"]
TARGET_COLUMN = "demand_count"
MODEL_VERSION = "lgbm-demand-v2"
SEED = 42


def build_national_weekly_series() -> tuple[pd.DataFrame, dict]:
    rentals = pd.read_parquet(DATA_DIR / "rentals.parquet")
    rentals["start_date"] = pd.to_datetime(rentals["start_date"])

    full_weeks = pd.date_range(
        rentals["start_date"].min().to_period("W").start_time,
        rentals["start_date"].max().to_period("W").start_time,
        freq="W-MON",
    )
    national = (
        rentals.set_index("start_date").resample("W-MON").size().reindex(full_weeks, fill_value=0)
    )
    df = national.rename("demand_count").reset_index().rename(columns={"index": "week_start"})

    # Each region's stable historical share of total demand, used to
    # disaggregate the national forecast back into per-region numbers.
    region_totals = rentals["region"].value_counts()
    region_share = (region_totals / region_totals.sum()).round(4).to_dict()

    return df, region_share


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("week_start").copy()
    for lag in [1, 2, 4]:
        df[f"lag_{lag}"] = df["demand_count"].shift(lag)
    df["rolling_mean_4"] = df["demand_count"].shift(1).rolling(4).mean()

    week_of_year = df["week_start"].dt.isocalendar().week.astype(int)
    df["week_of_year_sin"] = np.sin(2 * np.pi * week_of_year / 52)
    df["week_of_year_cos"] = np.cos(2 * np.pi * week_of_year / 52)
    df["week_index"] = np.arange(len(df))  # explicit trend signal - lag features alone
    # struggle to convey a slow drift with only ~70 training points

    df = df.dropna(subset=[f"lag_{l}" for l in [1, 2, 4]] + ["rolling_mean_4"]).reset_index(drop=True)
    return df


def train_and_evaluate(df: pd.DataFrame) -> tuple[lgb.LGBMRegressor, dict]:
    df = df.sort_values("week_start")
    split_idx = int(len(df) * 0.8)
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN]

    model = lgb.LGBMRegressor(
        n_estimators=100, max_depth=3, learning_rate=0.05, num_leaves=7,
        min_child_samples=5, subsample=0.9, colsample_bytree=0.9,
        reg_alpha=0.5, reg_lambda=0.5, random_state=SEED, verbose=-1,
    )
    model.fit(X_train, y_train)
    y_pred = np.clip(model.predict(X_test), 0, None)

    # Naive baseline (predict last observed value) - reported alongside the
    # model's own score so a negative-vs-baseline comparison is honest and
    # visible rather than hidden.
    naive_pred = test_df["lag_1"].values
    naive_mae = mean_absolute_error(y_test, naive_pred)

    metrics = {
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 3),
        "r2_score": round(float(r2_score(y_test, y_pred)), 4),
        "naive_baseline_mae": round(float(naive_mae), 3),
        "train_set_size": int(len(train_df)),
        "test_set_size": int(len(test_df)),
    }
    logger.info("Holdout test metrics: %s", json.dumps(metrics, indent=2))
    return model, metrics


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    weekly_df, region_share = build_national_weekly_series()
    logger.info("Built national weekly series: %d weeks.", len(weekly_df))

    featured_df = engineer_features(weekly_df)
    logger.info("After feature engineering: %d usable rows.", len(featured_df))

    model, metrics = train_and_evaluate(featured_df)
    joblib.dump(model, ARTIFACTS_DIR / "demand_model.joblib")

    latest = featured_df.sort_values("week_start").tail(1).iloc[0]
    meta = {
        "model_name": "demand_forecast",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "metrics": metrics,
        "granularity_trained_on": "weekly_national",
        "region_historical_share": region_share,
        "latest_state": {
            "week_start": str(latest["week_start"].date()),
            "demand_count": float(latest["demand_count"]),
            "lag_1": float(latest["lag_1"]),
            "lag_2": float(latest["lag_2"]),
            "lag_4": float(latest["lag_4"]),
            "rolling_mean_4": float(latest["rolling_mean_4"]),
        },
    }
    with open(ARTIFACTS_DIR / "demand_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.info("Saved model to %s", ARTIFACTS_DIR / "demand_model.joblib")


if __name__ == "__main__":
    run()

