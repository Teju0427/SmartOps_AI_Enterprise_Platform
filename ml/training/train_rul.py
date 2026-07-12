"""
Phase 3 — Remaining Useful Life (RUL) Model.

AI4I doesn't provide a direct RUL column, so the training target is
derived from AI4I's own documented failure mechanics: Tool Wear Failure
(TWF) in the source dataset is defined as occurring once accumulated
tool wear crosses a randomized threshold between 200-240 minutes. We use
that documented range to construct a physically-grounded RUL proxy:

    wear_capacity_remaining = wear_threshold - current_tool_wear
    rul_days = wear_capacity_remaining / assumed_daily_wear_rate

...further discounted by thermal/power stress (a machine running hot or
overpowered burns through its remaining life faster than wear alone
predicts), and floored at 0 for machines that have already failed.

A RandomForestRegressor learns to reproduce and generalize this proxy;
the ensemble's per-tree prediction spread is used to construct a
confidence interval (not just a point estimate), rather than bolting on
a separate quantile model — appropriate for this project's scope while
still giving the frontend a real interval to render.

Outputs (to ml/artifacts/):
    rul_model.joblib
    rul_model_meta.json

Run:
    python ml/training/train_rul.py
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.rul")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "datasets" / "processed" / "ai4i_clean.parquet"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"

FEATURE_COLUMNS = [
    "type_encoded", "air_temperature_k", "process_temperature_k",
    "rotational_speed_rpm", "torque_nm", "tool_wear_min",
    "temp_delta_k", "power_watts", "wear_torque_product", "tool_wear_ratio",
]
TARGET_COLUMN = "rul_days_proxy"
MODEL_VERSION = "rf-rul-v1"
SEED = 42

RAW_TO_SAFE_COLUMNS = {
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
}

# AI4I documentation: TWF occurs at a randomized wear threshold in [200, 240] min.
WEAR_THRESHOLD_MID = 220
DAILY_WEAR_RATE_MIN_PER_DAY = 8.0  # assumed typical industrial duty cycle


def build_rul_target(df: pd.DataFrame) -> pd.Series:
    wear_capacity_remaining = (WEAR_THRESHOLD_MID - df["tool_wear_min"]).clip(lower=0)
    base_rul_days = wear_capacity_remaining / DAILY_WEAR_RATE_MIN_PER_DAY

    # Thermal/power stress accelerates effective wear -> discount RUL further
    power_low, power_high = 3500, 9000
    power_stress = np.where(
        (df["power_watts"] >= power_low) & (df["power_watts"] <= power_high), 0.0,
        np.minimum(np.abs(df["power_watts"] - power_low) / power_low,
                   np.abs(df["power_watts"] - power_high) / power_high),
    )
    power_stress = np.clip(power_stress, 0, 1)
    temp_stress = np.clip((df["temp_delta_k"] - 12).clip(lower=0) / 8, 0, 1)
    stress_multiplier = 1 - 0.4 * np.maximum(power_stress, temp_stress)

    rul = base_rul_days * stress_multiplier
    rul = np.where(df["Machine failure"] == 1, 0.0, rul)  # already failed -> 0 RUL
    return pd.Series(rul, index=df.index).round(1)


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    encoder = LabelEncoder()
    df = df.rename(columns=RAW_TO_SAFE_COLUMNS).copy()
    df["type_encoded"] = encoder.fit_transform(df["Type"])
    df[TARGET_COLUMN] = build_rul_target(df)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y, encoder


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> tuple[RandomForestRegressor, dict, float]:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    model = RandomForestRegressor(
        n_estimators=300, max_depth=14, min_samples_split=4, min_samples_leaf=2,
        max_features="sqrt", random_state=SEED, n_jobs=-1,
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
    logger.info("5-fold CV R^2: mean=%.4f, std=%.4f", cv_scores.mean(), cv_scores.std())

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "mae_days": round(float(mean_absolute_error(y_test, y_pred)), 3),
        "r2_score": round(float(r2_score(y_test, y_pred)), 4),
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std": round(float(cv_scores.std()), 4),
        "test_set_size": int(len(y_test)),
    }

    # Per-tree prediction spread on the test set -> calibrate a symmetric
    # confidence-interval half-width to report alongside future point predictions.
    tree_preds = np.stack([tree.predict(X_test.values) for tree in model.estimators_], axis=0)
    tree_std = tree_preds.std(axis=0)
    metrics["mean_tree_std_days"] = round(float(tree_std.mean()), 3)

    logger.info("Holdout test metrics: %s", json.dumps(metrics, indent=2))
    return model, metrics, float(tree_std.mean())


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(DATA_PATH)
    logger.info("Loaded %d rows for training.", len(df))

    X, y, encoder = prepare_features(df)
    model, metrics, mean_tree_std = train_and_evaluate(X, y)

    joblib.dump(model, ARTIFACTS_DIR / "rul_model.joblib")

    meta = {
        "model_name": "remaining_useful_life",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "type_encoder_classes": encoder.classes_.tolist(),
        "metrics": metrics,
        "wear_threshold_mid_min": WEAR_THRESHOLD_MID,
        "daily_wear_rate_min_per_day": DAILY_WEAR_RATE_MIN_PER_DAY,
        "confidence_interval_half_width_days": round(mean_tree_std * 1.28, 2),  # ~80% CI
    }
    with open(ARTIFACTS_DIR / "rul_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.info("Saved model to %s", ARTIFACTS_DIR / "rul_model.joblib")


if __name__ == "__main__":
    run()
