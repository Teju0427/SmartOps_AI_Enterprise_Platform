"""Customer Intelligence — inference wrapper: CLV, late-payment risk, discount recommendation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import TypedDict
import joblib, pandas as pd

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class CustomerInput(TypedDict):
    industry: str
    region: str
    credit_limit: float
    tenure_days: int
    total_rentals: int
    avg_discount_pct: float
    avg_duration_days: float


class CustomerIntelligencePredictor:
    def __init__(self) -> None:
        meta_path = ARTIFACTS_DIR / "customer_intelligence_meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"{meta_path} not found. Run train_customer_intelligence.py first.")
        self.clv_model = joblib.load(ARTIFACTS_DIR / "clv_model.joblib")
        self.risk_model = joblib.load(ARTIFACTS_DIR / "risk_model.joblib")
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.encoders = self.meta["encoders"]
        self.discount_rule = self.meta["discount_rule"]
        self.clv_high_threshold = self.meta["clv_high_threshold"]

    def _encode(self, field: str, value: str) -> int:
        classes = self.encoders[field]
        if value not in classes:
            raise ValueError(f"Unknown {field} '{value}'. Expected one of {classes}.")
        return classes.index(value)

    def predict(self, payload: CustomerInput) -> dict:
        industry_e = self._encode("industry", payload["industry"])
        region_e = self._encode("region", payload["region"])

        clv_row = pd.DataFrame([{
            "industry_encoded": industry_e, "region_encoded": region_e,
            "credit_limit": payload["credit_limit"], "tenure_days": payload["tenure_days"],
        }])
        predicted_clv = max(0.0, float(self.clv_model.predict(clv_row)[0]))

        risk_row = pd.DataFrame([{
            "industry_encoded": industry_e, "region_encoded": region_e,
            "credit_limit": payload["credit_limit"], "tenure_days": payload["tenure_days"],
            "total_rentals": payload["total_rentals"], "avg_discount_pct": payload["avg_discount_pct"],
            "avg_duration_days": payload["avg_duration_days"],
        }])
        risk_proba = float(self.risk_model.predict_proba(risk_row)[0, 1])
        risk_tier = "high" if risk_proba >= 0.5 else ("medium" if risk_proba >= 0.25 else "low")

        # Discount recommendation - derived business rule combining CLV and risk
        discount = self.discount_rule["base_discount_pct"]
        if predicted_clv >= self.clv_high_threshold:
            discount += self.discount_rule["high_clv_bonus_pct"]
        if risk_tier == "high":
            discount -= self.discount_rule["high_risk_penalty_pct"]
        discount = max(self.discount_rule["min_discount_pct"], min(self.discount_rule["max_discount_pct"], discount))

        return {
            "predicted_lifetime_value": round(predicted_clv, 2),
            "late_payment_risk_probability": round(risk_proba, 4),
            "late_payment_risk_tier": risk_tier,
            "recommended_discount_pct": round(discount, 1),
            "model_version": self.meta["model_version"],
            "model_name": "customer_intelligence",
        }


if __name__ == "__main__":
    predictor = CustomerIntelligencePredictor()
    sample: CustomerInput = {
        "industry": "construction", "region": "Mumbai", "credit_limit": 150000,
        "tenure_days": 900, "total_rentals": 12, "avg_discount_pct": 4.5, "avg_duration_days": 18,
    }
    print("Prediction ->", predictor.predict(sample))
