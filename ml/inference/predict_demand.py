"""
Demand Forecasting — inference wrapper.

The trained model forecasts NATIONAL WEEKLY demand. This wrapper:
  1. Produces the weekly forecast using the model + persisted latest state.
  2. Derives daily/monthly/quarterly figures via calendar-based scaling
     of the weekly number (documented design decision - see
     train_demand_forecast.py docstring for why per-region/per-day
     modeling isn't reliable at this data volume).
  3. Disaggregates by region using each region's stable historical share.

Usage:
    from ml.inference.predict_demand import DemandPredictor
    predictor = DemandPredictor()
    result = predictor.forecast(granularity="weekly", region=None)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"

Granularity = Literal["daily", "weekly", "monthly", "quarterly"]

GRANULARITY_MULTIPLIER = {
    "daily": 1 / 7,
    "weekly": 1.0,
    "monthly": 4.345,   # average weeks per month
    "quarterly": 13.04,  # average weeks per quarter
}


class DemandPredictor:
    def __init__(self) -> None:
        model_path = ARTIFACTS_DIR / "demand_model.joblib"
        meta_path = ARTIFACTS_DIR / "demand_model_meta.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Demand model not found at {model_path}. "
                "Run `python ml/training/train_demand_forecast.py` first."
            )
        self.model = joblib.load(model_path)
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]
        self.region_share: dict[str, float] = self.meta["region_historical_share"]
        self.state = self.meta["latest_state"]

    def _next_week_features(self, week_offset: int, rolling_history: list[float]) -> pd.DataFrame:
        """Build features for forecasting `week_offset` weeks ahead of the
        last known data point, given the rolling history accumulated from
        prior forecast steps (needed for multi-step-ahead forecasting)."""
        last_week_start = pd.Timestamp(self.state["week_start"])
        target_week = last_week_start + pd.Timedelta(weeks=week_offset)
        week_of_year = target_week.isocalendar().week

        lag_1 = rolling_history[-1]
        lag_2 = rolling_history[-2] if len(rolling_history) >= 2 else lag_1
        lag_4 = rolling_history[-4] if len(rolling_history) >= 4 else lag_1
        rolling_mean_4 = float(np.mean(rolling_history[-4:]))

        row = {
            "lag_1": lag_1,
            "lag_2": lag_2,
            "lag_4": lag_4,
            "rolling_mean_4": rolling_mean_4,
            "week_of_year_sin": np.sin(2 * np.pi * week_of_year / 52),
            "week_of_year_cos": np.cos(2 * np.pi * week_of_year / 52),
        }
        if "week_index" in self.feature_columns:
            row["week_index"] = 999_999  # far-future index; trend feature not used at inference time
        return pd.DataFrame([row])[self.feature_columns]

    def forecast_weekly_series(self, n_weeks: int = 4) -> list[float]:
        """Multi-step-ahead weekly forecast, feeding each prediction back
        in as the next step's lag_1 (standard recursive forecasting)."""
        history = [
            self.state["lag_4"], self.state["lag_2"], self.state["lag_1"], self.state["demand_count"],
        ]
        forecasts = []
        for step in range(1, n_weeks + 1):
            X = self._next_week_features(step, history)
            pred = max(0.0, float(self.model.predict(X)[0]))
            forecasts.append(pred)
            history.append(pred)
        return forecasts

    def forecast(self, granularity: Granularity = "weekly", region: str | None = None,
                 periods: int = 1) -> dict:
        multiplier = GRANULARITY_MULTIPLIER[granularity]
        # Forecast enough weeks ahead to cover the requested periods at this granularity
        weeks_needed = max(1, int(np.ceil(periods * multiplier)))
        weekly_forecasts = self.forecast_weekly_series(n_weeks=weeks_needed)
        avg_weekly_rate = float(np.mean(weekly_forecasts))
        national_value = avg_weekly_rate * multiplier

        if region is not None:
            if region not in self.region_share:
                raise ValueError(f"Unknown region '{region}'. Expected one of {list(self.region_share)}.")
            value = national_value * self.region_share[region]
        else:
            value = national_value

        return {
            "granularity": granularity,
            "region": region or "national",
            "forecasted_demand": round(value, 1),
            "model_version": self.meta["model_version"],
            "model_name": "demand_forecast",
        }

    def forecast_all_regions(self, granularity: Granularity = "weekly") -> list[dict]:
        return [self.forecast(granularity=granularity, region=r) for r in self.region_share]


if __name__ == "__main__":
    predictor = DemandPredictor()

    for g in ["daily", "weekly", "monthly", "quarterly"]:
        print(f"National {g} forecast ->", predictor.forecast(granularity=g))

    print("\nMumbai weekly forecast ->", predictor.forecast(granularity="weekly", region="Mumbai"))
