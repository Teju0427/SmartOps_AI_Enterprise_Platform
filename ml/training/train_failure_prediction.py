"""
Phase 3 — Failure Prediction Model.

Trains an XGBoost binary classifier predicting `Machine failure` from the
AI4I sensor features, using the FULL cleaned 10,000-row sensor pool (not
just the 420-machine sampled fleet) — more training data means a better
model, and the trained model will later score the fleet's live health
regardless of which machines happen to be in the current sample.

Outputs (to ml/artifacts/):
    failure_model.joblib       - trained XGBoost model
    failure_model_meta.json    - feature list, encoder classes, metrics, version
    failure_shap_summary.json  - global SHAP feature importance

Run:
    python ml/training/train_failure_prediction.py
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
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.failure_prediction")

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
TARGET_COLUMN = "Machine failure"
MODEL_VERSION = "xgb-failure-v1"
SEED = 42

# Raw AI4I column names contain brackets (e.g. "Air temperature [K]") which
# XGBoost's feature-name validation rejects outright - rename to safe,
# bracket-free identifiers before handing features to the model.
RAW_TO_SAFE_COLUMNS = {
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
}


def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    logger.info("Loaded %d rows for training.", len(df))
    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    encoder = LabelEncoder()
    df = df.copy()
    df = df.rename(columns=RAW_TO_SAFE_COLUMNS)
    df["type_encoded"] = encoder.fit_transform(df["Type"])
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y, encoder


def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> tuple[xgb.XGBClassifier, dict]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED
    )

    # Class imbalance handling: failures are ~3.4% of rows. scale_pos_weight
    # tells XGBoost to weight the minority (failure) class proportionally,
    # rather than the model trivially predicting "no failure" for everything.
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    logger.info("Class balance -> negatives: %d, positives: %d, scale_pos_weight: %.2f",
                (y_train == 0).sum(), (y_train == 1).sum(), scale_pos_weight)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=SEED,
        n_jobs=-1,
    )

    # Manual K-fold loop rather than sklearn's cross_val_score: XGBoost 2.1.x
    # doesn't fully implement scikit-learn 1.6's new estimator-tags API,
    # which crashes cross_val_score's internal is_classifier() check.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    fold_scores = []
    for train_idx, val_idx in cv.split(X_train, y_train):
        fold_model = xgb.XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.85,
            colsample_bytree=0.85, min_child_weight=3, scale_pos_weight=scale_pos_weight,
            eval_metric="aucpr", random_state=SEED, n_jobs=-1,
        )
        fold_model.fit(X_train.iloc[train_idx], y_train.iloc[train_idx])
        fold_proba = fold_model.predict_proba(X_train.iloc[val_idx])[:, 1]
        fold_scores.append(average_precision_score(y_train.iloc[val_idx], fold_proba))
    cv_scores = np.array(fold_scores)
    logger.info("5-fold CV average precision (PR-AUC): mean=%.4f, std=%.4f", cv_scores.mean(), cv_scores.std())

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "pr_auc": round(float(average_precision_score(y_test, y_proba)), 4),
        "cv_pr_auc_mean": round(float(cv_scores.mean()), 4),
        "cv_pr_auc_std": round(float(cv_scores.std()), 4),
        "test_set_size": int(len(y_test)),
        "test_set_positives": int(y_test.sum()),
    }
    cm = confusion_matrix(y_test, y_pred)
    metrics["confusion_matrix"] = {
        "true_negative": int(cm[0][0]), "false_positive": int(cm[0][1]),
        "false_negative": int(cm[1][0]), "true_positive": int(cm[1][1]),
    }

    logger.info("Holdout test metrics: %s", json.dumps(metrics, indent=2))
    return model, metrics


def compute_shap_summary(model: xgb.XGBClassifier, X: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    sample = X.sample(n=min(1000, len(X)), random_state=SEED)
    shap_values = explainer.shap_values(sample)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = sorted(
        zip(X.columns.tolist(), mean_abs_shap.tolist()),
        key=lambda t: t[1],
        reverse=True,
    )
    return {"global_feature_importance": [{"feature": f, "mean_abs_shap": round(v, 5)} for f, v in importance]}


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    X, y, encoder = prepare_features(df)
    model, metrics = train_and_evaluate(X, y)
    shap_summary = compute_shap_summary(model, X)

    joblib.dump(model, ARTIFACTS_DIR / "failure_model.joblib")

    meta = {
        "model_name": "failure_prediction",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "type_encoder_classes": encoder.classes_.tolist(),
        "metrics": metrics,
        "risk_tier_thresholds": {"low": 0.15, "medium": 0.45},  # >=0.45 -> high risk
    }
    with open(ARTIFACTS_DIR / "failure_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    with open(ARTIFACTS_DIR / "failure_shap_summary.json", "w") as f:
        json.dump(shap_summary, f, indent=2)

    logger.info("Saved model to %s", ARTIFACTS_DIR / "failure_model.joblib")
    logger.info("Top SHAP features:\n%s", json.dumps(shap_summary["global_feature_importance"][:5], indent=2))


if __name__ == "__main__":
    run()
