"""
Remaining Useful Life — inference wrapper.

Usage:
    from ml.inference.predict_rul import RULPredictor
    predictor = RULPredictor()
    result = predictor.predict({...})
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


class RULPredictionInput(TypedDict):
    type: str
    air_temperature_k: float
    process_temperature_k: float
    rotational_speed_rpm: float
    torque_nm: float
    tool_wear_min: float


class RULPredictor:
    def __init__(self) -> None:
        model_path = ARTIFACTS_DIR / "rul_model.joblib"
        meta_path = ARTIFACTS_DIR / "rul_model_meta.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"RUL model not found at {model_path}. Run `python ml/training/train_rul.py` first."
            )
        self.model = joblib.load(model_path)
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]
        self.type_classes: list[str] = self.meta["type_encoder_classes"]
        self.ci_half_width = self.meta["confidence_interval_half_width_days"]

    def _engineer(self, payload: RULPredictionInput) -> pd.DataFrame:
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

    def predict(self, payload: RULPredictionInput) -> dict:
        X = self._engineer(payload)
        point_estimate = float(self.model.predict(X)[0])
        point_estimate = max(0.0, point_estimate)

        lower = max(0.0, point_estimate - self.ci_half_width)
        upper = point_estimate + self.ci_half_width

        return {
            "remaining_useful_life_days": round(point_estimate, 1),
            "confidence_interval_lower_days": round(lower, 1),
            "confidence_interval_upper_days": round(upper, 1),
            "model_version": self.meta["model_version"],
            "model_name": "remaining_useful_life",
        }

    def predict_batch(self, payloads: list[RULPredictionInput]) -> list[dict]:
        return [self.predict(p) for p in payloads]


if __name__ == "__main__":
    predictor = RULPredictor()

    fresh_sample: RULPredictionInput = {
        "type": "M", "air_temperature_k": 298.1, "process_temperature_k": 308.6,
        "rotational_speed_rpm": 1551, "torque_nm": 42.8, "tool_wear_min": 5,
    }
    worn_sample: RULPredictionInput = {
        "type": "L", "air_temperature_k": 300.0, "process_temperature_k": 309.0,
        "rotational_speed_rpm": 1450, "torque_nm": 45.0, "tool_wear_min": 195,
    }

    print("Fresh machine  ->", predictor.predict(fresh_sample))
    print("Worn machine   ->", predictor.predict(worn_sample))
