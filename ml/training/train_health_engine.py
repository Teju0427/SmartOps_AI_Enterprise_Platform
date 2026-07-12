"""
Phase 3 — Equipment Health Engine.

Trains a Random Forest regressor to predict the 0-100 equipment health
score from raw sensor features. The training target is the calibrated
heuristic health score computed in the Phase 2 ETL stage
(etl_ai4i_clean.py::engineer_features) — a domain-logic scoring function
grounded in AI4I's own documented failure thresholds (tool wear, power
band, temperature delta) plus the actual failure outcome.

Training a model against this heuristic (rather than shipping the
heuristic directly) buys two things a hardcoded formula can't:
  1. Smooth generalization to sensor combinations never seen in the
     heuristic's explicit rules.
  2. Per-machine SHAP explainability ("why is THIS machine at 62/100"),
     which a fixed formula can only explain by re-deriving the whole
     calculation by hand.

Outputs (to ml/artifacts/):
    health_model.joblib
    health_model_meta.json

Run:
    python ml/training/train_health_engine.py
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.health_engine")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "datasets" / "processed" / "ai4i_clean.parquet"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"

FEATURE_COLUMNS = [
    "type_encoded",
    "air_temperature_k",
    "process_temperature_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
    "temp_delta_k",
    "power_watts",
    "wear_torque_product",
    "tool_wear_ratio",
]
TARGET_COLUMN = "heuristic_health_score"
MODEL_VERSION = "rf-health-v1"
SEED = 42

RAW_TO_SAFE_COLUMNS = {
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
}


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    encoder = LabelEncoder()
    df = df.rename(columns=RAW_TO_SAFE_COLUMNS).copy()
    df["type_encoded"] = encoder.fit_transform(df["Type"])
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y, encoder


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> tuple[RandomForestRegressor, dict]:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=SEED,
        n_jobs=-1,
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
    logger.info("5-fold CV R^2: mean=%.4f, std=%.4f", cv_scores.mean(), cv_scores.std())

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
        "r2_score": round(float(r2_score(y_test, y_pred)), 4),
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std": round(float(cv_scores.std()), 4),
        "test_set_size": int(len(y_test)),
    }
    logger.info("Holdout test metrics: %s", json.dumps(metrics, indent=2))
    return model, metrics


def compute_shap_summary(model: RandomForestRegressor, X: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    sample = X.sample(n=min(800, len(X)), random_state=SEED)
    shap_values = explainer.shap_values(sample)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = sorted(zip(X.columns.tolist(), mean_abs_shap.tolist()), key=lambda t: t[1], reverse=True)
    return {"global_feature_importance": [{"feature": f, "mean_abs_shap": round(v, 5)} for f, v in importance]}


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(DATA_PATH)
    logger.info("Loaded %d rows for training.", len(df))

    X, y, encoder = prepare_features(df)
    model, metrics = train_and_evaluate(X, y)
    shap_summary = compute_shap_summary(model, X)

    joblib.dump(model, ARTIFACTS_DIR / "health_model.joblib")

    meta = {
        "model_name": "equipment_health",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "type_encoder_classes": encoder.classes_.tolist(),
        "metrics": metrics,
        "status_thresholds": {"healthy": 70, "warning": 40},  # below 40 -> critical
    }
    with open(ARTIFACTS_DIR / "health_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    with open(ARTIFACTS_DIR / "health_shap_summary.json", "w") as f:
        json.dump(shap_summary, f, indent=2)

    logger.info("Saved model to %s", ARTIFACTS_DIR / "health_model.joblib")
    logger.info("Top SHAP features:\n%s", json.dumps(shap_summary["global_feature_importance"][:5], indent=2))


if __name__ == "__main__":
    run()
