"""
Failure Prediction — inference wrapper.

Loads the trained model once and exposes a simple `predict()` function
the FastAPI layer (Phase 7-8) will call. Kept dependency-free from the
web framework so it can also be used directly from ETL/batch scripts.

Usage:
    from ml.inference.predict_failure import FailurePredictor
    predictor = FailurePredictor()
    result = predictor.predict({
        "type": "M", "air_temperature_k": 298.1, "process_temperature_k": 308.6,
        "rotational_speed_rpm": 1551, "torque_nm": 42.8, "tool_wear_min": 0,
    })
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict

import joblib
import numpy as np
import pandas as pd

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class FailurePredictionInput(TypedDict):
    type: str  # "L", "M", or "H"
    air_temperature_k: float
    process_temperature_k: float
    rotational_speed_rpm: float
    torque_nm: float
    tool_wear_min: float


class FailurePredictor:
    def __init__(self) -> None:
        model_path = ARTIFACTS_DIR / "failure_model.joblib"
        meta_path = ARTIFACTS_DIR / "failure_model_meta.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Failure model not found at {model_path}. "
                "Run `python ml/training/train_failure_prediction.py` first."
            )
        self.model = joblib.load(model_path)
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]
        self.type_classes: list[str] = self.meta["type_encoder_classes"]
        self.thresholds = self.meta["risk_tier_thresholds"]

    def _engineer(self, payload: FailurePredictionInput) -> pd.DataFrame:
        if payload["type"] not in self.type_classes:
            raise ValueError(f"Unknown equipment Type '{payload['type']}'. Expected one of {self.type_classes}.")
        type_encoded = self.type_classes.index(payload["type"])

        temp_delta = payload["process_temperature_k"] - payload["air_temperature_k"]
        power_watts = payload["torque_nm"] * (payload["rotational_speed_rpm"] * 2 * math.pi / 60)
        wear_torque_product = payload["tool_wear_min"] * payload["torque_nm"]
        tool_wear_ratio = min(payload["tool_wear_min"] / 200, 1.0)

        row = {
            "type_encoded": type_encoded,
            "air_temperature_k": payload["air_temperature_k"],
            "process_temperature_k": payload["process_temperature_k"],
            "rotational_speed_rpm": payload["rotational_speed_rpm"],
            "torque_nm": payload["torque_nm"],
            "tool_wear_min": payload["tool_wear_min"],
            "temp_delta_k": temp_delta,
            "power_watts": power_watts,
            "wear_torque_product": wear_torque_product,
            "tool_wear_ratio": tool_wear_ratio,
        }
        return pd.DataFrame([row])[self.feature_columns]

    def _risk_tier(self, probability: float) -> str:
        if probability < self.thresholds["low"]:
            return "low"
        if probability < self.thresholds["medium"]:
            return "medium"
        return "high"

    def predict(self, payload: FailurePredictionInput) -> dict:
        X = self._engineer(payload)
        probability = float(self.model.predict_proba(X)[0, 1])
        return {
            "failure_probability": round(probability, 4),
            "risk_tier": self._risk_tier(probability),
            "model_version": self.meta["model_version"],
            "model_name": "failure_prediction",
        }

    def predict_batch(self, payloads: list[FailurePredictionInput]) -> list[dict]:
        return [self.predict(p) for p in payloads]


if __name__ == "__main__":
    # Quick smoke test against a known-healthy and known-risky profile
    predictor = FailurePredictor()

    healthy_sample: FailurePredictionInput = {
        "type": "M", "air_temperature_k": 298.1, "process_temperature_k": 308.6,
        "rotational_speed_rpm": 1551, "torque_nm": 42.8, "tool_wear_min": 5,
    }
    risky_sample: FailurePredictionInput = {
        "type": "L", "air_temperature_k": 302.5, "process_temperature_k": 311.8,
        "rotational_speed_rpm": 1350, "torque_nm": 65.0, "tool_wear_min": 215,
    }

    print("Healthy profile ->", predictor.predict(healthy_sample))
    print("Risky profile   ->", predictor.predict(risky_sample))
