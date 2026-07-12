"""
Equipment Health Engine — inference wrapper.

Usage:
    from ml.inference.predict_health import HealthPredictor
    predictor = HealthPredictor()
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
import pandas as pd

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class HealthPredictionInput(TypedDict):
    type: str
    air_temperature_k: float
    process_temperature_k: float
    rotational_speed_rpm: float
    torque_nm: float
    tool_wear_min: float


class HealthPredictor:
    def __init__(self) -> None:
        model_path = ARTIFACTS_DIR / "health_model.joblib"
        meta_path = ARTIFACTS_DIR / "health_model_meta.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Health model not found at {model_path}. "
                "Run `python ml/training/train_health_engine.py` first."
            )
        self.model = joblib.load(model_path)
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]
        self.type_classes: list[str] = self.meta["type_encoder_classes"]
        self.thresholds = self.meta["status_thresholds"]

    def _engineer(self, payload: HealthPredictionInput) -> pd.DataFrame:
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

    def _status(self, score: float) -> str:
        if score >= self.thresholds["healthy"]:
            return "healthy"
        if score >= self.thresholds["warning"]:
            return "warning"
        return "critical"

    def predict(self, payload: HealthPredictionInput) -> dict:
        X = self._engineer(payload)
        score = float(self.model.predict(X)[0])
        score = max(0.0, min(100.0, score))
        return {
            "health_score": round(score, 1),
            "status": self._status(score),
            "model_version": self.meta["model_version"],
            "model_name": "equipment_health",
        }

    def predict_batch(self, payloads: list[HealthPredictionInput]) -> list[dict]:
        return [self.predict(p) for p in payloads]


if __name__ == "__main__":
    predictor = HealthPredictor()

    healthy_sample: HealthPredictionInput = {
        "type": "M", "air_temperature_k": 298.1, "process_temperature_k": 308.6,
        "rotational_speed_rpm": 1551, "torque_nm": 42.8, "tool_wear_min": 5,
    }
    degraded_sample: HealthPredictionInput = {
        "type": "L", "air_temperature_k": 302.5, "process_temperature_k": 311.8,
        "rotational_speed_rpm": 1350, "torque_nm": 65.0, "tool_wear_min": 190,
    }

    print("Healthy profile  ->", predictor.predict(healthy_sample))
    print("Degraded profile ->", predictor.predict(degraded_sample))
