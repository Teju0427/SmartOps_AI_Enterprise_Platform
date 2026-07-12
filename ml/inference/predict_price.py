"""
Dynamic Price Prediction — inference wrapper.

Returns suggested price, a confidence score, AND a human-readable
reasoning string built from that specific prediction's SHAP values —
satisfying the spec's requirement to return "Suggested Price, Confidence
Score, Reasoning" as three distinct outputs, not just a number.

Usage:
    from ml.inference.predict_price import PricePredictor
    predictor = PricePredictor()
    result = predictor.predict({...})
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import joblib
import numpy as np
import pandas as pd
import shap

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"

FEATURE_LABELS = {
    "equipment_type_encoded": "equipment type",
    "health_score": "equipment health",
    "market_competitor_price": "competitor pricing",
    "duration_days_planned": "rental duration",
    "industry_encoded": "customer industry",
    "region_encoded": "region",
    "inventory_count": "inventory availability",
    "month_sin": "seasonal demand pattern",
    "month_cos": "seasonal demand pattern",
    "base_daily_rate": "equipment base rate",
}


class PricePredictionInput(TypedDict):
    equipment_type: str
    health_score: float
    market_competitor_price: float
    duration_days_planned: int
    industry: str
    region: str
    inventory_count: int
    month: int  # 1-12
    base_daily_rate: float


class PricePredictor:
    def __init__(self) -> None:
        model_path = ARTIFACTS_DIR / "price_model.joblib"
        meta_path = ARTIFACTS_DIR / "price_model_meta.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Price model not found at {model_path}. "
                "Run `python ml/training/train_price_prediction.py` first."
            )
        self.model = joblib.load(model_path)
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]
        self.encoders = self.meta["encoders"]
        self.explainer = shap.TreeExplainer(self.model)
        self.mae = self.meta["metrics"]["mae"]

    def _encode(self, field: str, value: str) -> int:
        classes: list[str] = self.encoders[field]
        if value not in classes:
            raise ValueError(f"Unknown {field} '{value}'. Expected one of {classes}.")
        return classes.index(value)

    def _engineer(self, payload: PricePredictionInput) -> pd.DataFrame:
        month_sin = np.sin(2 * np.pi * payload["month"] / 12)
        month_cos = np.cos(2 * np.pi * payload["month"] / 12)

        row = {
            "equipment_type_encoded": self._encode("equipment_type", payload["equipment_type"]),
            "health_score": payload["health_score"],
            "market_competitor_price": payload["market_competitor_price"],
            "duration_days_planned": payload["duration_days_planned"],
            "industry_encoded": self._encode("industry", payload["industry"]),
            "region_encoded": self._encode("region", payload["region"]),
            "inventory_count": payload["inventory_count"],
            "month_sin": month_sin,
            "month_cos": month_cos,
            "base_daily_rate": payload["base_daily_rate"],
        }
        return pd.DataFrame([row])[self.feature_columns]

    def _reasoning(self, X: pd.DataFrame, predicted_price: float) -> str:
        shap_values = self.explainer.shap_values(X)[0]
        contributions = sorted(
            zip(self.feature_columns, shap_values), key=lambda t: abs(t[1]), reverse=True
        )[:3]

        parts = []
        for feature, value in contributions:
            label = FEATURE_LABELS.get(feature, feature)
            direction = "increased" if value > 0 else "decreased"
            parts.append(f"{label} {direction} the price by ~${abs(value):.0f}")

        return f"Suggested rate of ${predicted_price:.2f}/day, driven primarily by: " + "; ".join(parts) + "."

    def _confidence(self, X: pd.DataFrame, predicted_price: float) -> float:
        # Confidence derived from the model's own historical MAE relative to
        # the magnitude of this specific prediction - a $5,000/day machine
        # being off by the average $5.54 MAE is far more confident (in
        # relative terms) than a $50/day machine off by the same amount.
        relative_error = self.mae / max(predicted_price, 1.0)
        confidence = max(0.5, min(0.99, 1 - relative_error))
        return round(confidence, 3)

    def predict(self, payload: PricePredictionInput) -> dict:
        X = self._engineer(payload)
        predicted_price = float(self.model.predict(X)[0])
        predicted_price = max(0.0, predicted_price)

        return {
            "suggested_price": round(predicted_price, 2),
            "confidence_score": self._confidence(X, predicted_price),
            "reasoning": self._reasoning(X, predicted_price),
            "model_version": self.meta["model_version"],
            "model_name": "price_prediction",
        }

    def predict_batch(self, payloads: list[PricePredictionInput]) -> list[dict]:
        return [self.predict(p) for p in payloads]


if __name__ == "__main__":
    predictor = PricePredictor()

    sample: PricePredictionInput = {
        "equipment_type": "excavator",
        "health_score": 88.0,
        "market_competitor_price": 1500.0,
        "duration_days_planned": 14,
        "industry": "construction",
        "region": "Mumbai",
        "inventory_count": 3,
        "month": 7,
        "base_daily_rate": 1400.0,
    }
    print("Prediction ->", predictor.predict(sample))
