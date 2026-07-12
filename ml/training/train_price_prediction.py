"""
Phase 3 — Dynamic Rental Price Prediction.

Trains an XGBoost regressor to predict the optimal daily rental price
from: equipment health, equipment type, competitor price, rental
duration, customer industry, region, inventory availability, and
seasonality (a proxy for "market conditions"). Training target is the
`ai_suggested_price` generated during Phase 2 ETL — itself a domain-
grounded function of base rate, competitor price, equipment health, and
duration discounting — so the model learns to reproduce and generalize
that pricing logic to rental scenarios never explicitly seen.

Outputs (to ml/artifacts/):
    price_model.joblib
    price_model_meta.json
    price_shap_summary.json

Run:
    python ml/training/train_price_prediction.py
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
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.price_prediction")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"

FEATURE_COLUMNS = [
    "equipment_type_encoded", "health_score", "market_competitor_price",
    "duration_days_planned", "industry_encoded", "region_encoded",
    "inventory_count", "month_sin", "month_cos", "base_daily_rate",
]
TARGET_COLUMN = "ai_suggested_price"
MODEL_VERSION = "xgb-price-v1"
SEED = 42


def build_training_set() -> pd.DataFrame:
    rentals = pd.read_parquet(DATA_DIR / "rentals.parquet")
    fleet = pd.read_parquet(DATA_DIR / "equipment_fleet.parquet")
    customers = pd.read_parquet(DATA_DIR / "customers.parquet")

    # Inventory proxy: how many machines of the same type currently sit in
    # the same region - low count = scarcer = should push price up, which
    # is exactly the kind of signal a real inventory-optimization feed
    # would supply.
    inventory_counts = (
        fleet.groupby(["equipment_type", "current_region"]).size().rename("inventory_count").reset_index()
    )

    df = rentals.merge(
        fleet[["equipment_id", "equipment_type", "heuristic_health_score", "base_daily_rate"]],
        on="equipment_id", how="inner",
    )
    df = df.merge(customers[["customer_id", "industry"]], on="customer_id", how="inner")
    df = df.merge(inventory_counts, left_on=["equipment_type", "region"],
                   right_on=["equipment_type", "current_region"], how="left")
    df["inventory_count"] = df["inventory_count"].fillna(1)

    df["health_score"] = df["heuristic_health_score"]

    # Seasonality / "market conditions" proxy - cyclical month encoding
    # avoids the false "December is far from January" discontinuity a raw
    # month-number feature would introduce.
    month = pd.to_datetime(df["start_date"]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * month / 12)
    df["month_cos"] = np.cos(2 * np.pi * month / 12)

    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict[str, LabelEncoder]]:
    encoders = {}
    df = df.copy()
    for col, enc_name in [("equipment_type", "equipment_type_encoded"),
                           ("industry", "industry_encoded"),
                           ("region", "region_encoded")]:
        le = LabelEncoder()
        df[enc_name] = le.fit_transform(df[col])
        encoders[col] = le

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y, encoders


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> tuple[xgb.XGBRegressor, dict]:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    def make_model() -> xgb.XGBRegressor:
        return xgb.XGBRegressor(
            n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.85,
            colsample_bytree=0.85, min_child_weight=3, random_state=SEED, n_jobs=-1,
            eval_metric="mae",
        )

    # Manual K-fold loop rather than sklearn's cross_val_score: XGBoost 2.1.x's
    # XGBRegressor doesn't fully implement scikit-learn 1.6's new estimator-tags
    # API, which crashes cross_val_score's internal is_classifier() check. A
    # plain loop sidesteps that fragile auto-detection path entirely.
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)
    fold_scores = []
    for train_idx, val_idx in cv.split(X_train):
        fold_model = make_model()
        fold_model.fit(X_train.iloc[train_idx], y_train.iloc[train_idx])
        fold_pred = fold_model.predict(X_train.iloc[val_idx])
        fold_scores.append(r2_score(y_train.iloc[val_idx], fold_pred))
    cv_scores = np.array(fold_scores)
    logger.info("5-fold CV R^2: mean=%.4f, std=%.4f", cv_scores.mean(), cv_scores.std())

    model = make_model()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 2),
        "mape": round(float(mean_absolute_percentage_error(y_test, y_pred)) * 100, 2),
        "r2_score": round(float(r2_score(y_test, y_pred)), 4),
        "cv_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_r2_std": round(float(cv_scores.std()), 4),
        "test_set_size": int(len(y_test)),
    }
    logger.info("Holdout test metrics: %s", json.dumps(metrics, indent=2))
    return model, metrics


def compute_shap_summary(model: xgb.XGBRegressor, X: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    sample = X.sample(n=min(800, len(X)), random_state=SEED)
    shap_values = explainer.shap_values(sample)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = sorted(zip(X.columns.tolist(), mean_abs_shap.tolist()), key=lambda t: t[1], reverse=True)
    return {"global_feature_importance": [{"feature": f, "mean_abs_shap": round(v, 5)} for f, v in importance]}


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = build_training_set()
    logger.info("Built training set: %d rows", len(df))

    X, y, encoders = prepare_features(df)
    model, metrics = train_and_evaluate(X, y)
    shap_summary = compute_shap_summary(model, X)

    joblib.dump(model, ARTIFACTS_DIR / "price_model.joblib")

    meta = {
        "model_name": "price_prediction",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "encoders": {name: enc.classes_.tolist() for name, enc in encoders.items()},
        "metrics": metrics,
    }
    with open(ARTIFACTS_DIR / "price_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    with open(ARTIFACTS_DIR / "price_shap_summary.json", "w") as f:
        json.dump(shap_summary, f, indent=2)

    logger.info("Saved model to %s", ARTIFACTS_DIR / "price_model.joblib")
    logger.info("Top SHAP features:\n%s", json.dumps(shap_summary["global_feature_importance"][:5], indent=2))


if __name__ == "__main__":
    run()
