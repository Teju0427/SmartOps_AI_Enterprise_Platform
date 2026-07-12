"""Phase 3 — Customer Intelligence. CLV regression (RandomForest), late-payment
risk classifier (XGBoost), discount recommendation (derived rule from risk+CLV)."""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
import joblib, numpy as np, pandas as pd, xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train.customer_intelligence")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
SEED = 42

CLV_FEATURES = ["industry_encoded", "region_encoded", "credit_limit", "tenure_days"]
RISK_FEATURES = ["industry_encoded", "region_encoded", "credit_limit", "tenure_days",
                  "total_rentals", "avg_discount_pct", "avg_duration_days"]


def build_customer_dataset() -> pd.DataFrame:
    customers = pd.read_parquet(DATA_DIR / "customers.parquet")
    rentals = pd.read_parquet(DATA_DIR / "rentals.parquet")
    rentals = rentals.dropna(subset=["total_revenue"])

    agg = rentals.groupby("customer_id").agg(
        total_rentals=("rental_id", "count"),
        total_revenue=("total_revenue", "sum"),
        avg_discount_pct=("discount_applied_pct", "mean"),
        avg_duration_days=("duration_days_planned", "mean"),
        late_payment_rate=("is_late_payment", "mean"),
    ).reset_index()

    df = customers.merge(agg, on="customer_id", how="left")
    df[["total_rentals", "total_revenue", "avg_discount_pct", "avg_duration_days", "late_payment_rate"]] = \
        df[["total_rentals", "total_revenue", "avg_discount_pct", "avg_duration_days", "late_payment_rate"]].fillna(0)

    df["onboarded_date"] = pd.to_datetime(df["onboarded_date"])
    df["tenure_days"] = (pd.Timestamp.today() - df["onboarded_date"]).dt.days
    df["is_high_late_risk"] = (df["late_payment_rate"] > 0.05).astype(int)
    return df


def train_clv(df: pd.DataFrame) -> tuple[RandomForestRegressor, dict, dict]:
    encoders = {}
    d = df.copy()
    for col in ["industry", "region"]:
        le = LabelEncoder()
        d[f"{col}_encoded"] = le.fit_transform(d[col])
        encoders[col] = le

    X, y = d[CLV_FEATURES], d["total_revenue"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)
    model = RandomForestRegressor(n_estimators=250, max_depth=8, min_samples_leaf=3, random_state=SEED, n_jobs=-1)
    model.fit(X_train, y_train)
    pred = np.clip(model.predict(X_test), 0, None)
    metrics = {"mae": round(float(mean_absolute_error(y_test, pred)), 2),
               "r2_score": round(float(r2_score(y_test, pred)), 4), "test_set_size": int(len(y_test))}
    logger.info("CLV metrics: %s", json.dumps(metrics))
    return model, metrics, encoders


def train_risk(df: pd.DataFrame, encoders: dict) -> tuple[xgb.XGBClassifier, dict]:
    d = df.copy()
    d["industry_encoded"] = encoders["industry"].transform(d["industry"])
    d["region_encoded"] = encoders["region"].transform(d["region"])

    X, y = d[RISK_FEATURES], d["is_high_late_risk"]
    if y.sum() < 3:
        logger.warning("Very few high-risk customers (%d) - training on full data, skipping holdout AUC.", y.sum())
        model = xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.08, random_state=SEED, eval_metric="logloss")
        model.fit(X, y)
        return model, {"note": "insufficient positive examples for holdout evaluation", "positive_count": int(y.sum())}

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.08,
                               scale_pos_weight=scale_pos_weight, random_state=SEED, eval_metric="logloss")
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    pred = model.predict(X_test)
    metrics = {"accuracy": round(float(accuracy_score(y_test, pred)), 4),
               "f1_score": round(float(f1_score(y_test, pred, zero_division=0)), 4),
               "roc_auc": round(float(roc_auc_score(y_test, proba)), 4) if y_test.nunique() > 1 else None,
               "test_set_size": int(len(y_test)), "positive_count": int(y.sum())}
    logger.info("Risk metrics: %s", json.dumps(metrics))
    return model, metrics


def run() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = build_customer_dataset()
    logger.info("Customer dataset: %d rows", len(df))

    clv_model, clv_metrics, encoders = train_clv(df)
    risk_model, risk_metrics = train_risk(df, encoders)

    joblib.dump(clv_model, ARTIFACTS_DIR / "clv_model.joblib")
    joblib.dump(risk_model, ARTIFACTS_DIR / "risk_model.joblib")

    meta = {
        "model_name": "customer_intelligence", "model_version": "rf-xgb-customer-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "clv_feature_columns": CLV_FEATURES, "risk_feature_columns": RISK_FEATURES,
        "encoders": {name: enc.classes_.tolist() for name, enc in encoders.items()},
        "clv_metrics": clv_metrics, "risk_metrics": risk_metrics,
        "discount_rule": {
            "base_discount_pct": 3.0, "high_clv_percentile": 0.75, "high_clv_bonus_pct": 4.0,
            "high_risk_penalty_pct": 3.0, "max_discount_pct": 12.0, "min_discount_pct": 0.0,
        },
        "clv_high_threshold": float(df["total_revenue"].quantile(0.75)),
    }
    with open(ARTIFACTS_DIR / "customer_intelligence_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved CLV + risk models.")


if __name__ == "__main__":
    run()
