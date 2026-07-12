"""Revenue Forecasting — inference wrapper. Weekly revenue/profit + utilization."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Literal
import joblib, numpy as np, pandas as pd

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
Granularity = Literal["weekly", "monthly", "quarterly"]
MULTIPLIER = {"weekly": 1.0, "monthly": 4.345, "quarterly": 13.04}


class RevenuePredictor:
    def __init__(self) -> None:
        meta_path = ARTIFACTS_DIR / "revenue_model_meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"{meta_path} not found. Run train_revenue_forecast.py first.")
        self.revenue_model = joblib.load(ARTIFACTS_DIR / "revenue_model.joblib")
        self.profit_model = joblib.load(ARTIFACTS_DIR / "profit_model.joblib")
        with open(meta_path) as f:
            self.meta = json.load(f)
        self.feature_columns = self.meta["feature_columns"]

    def _row(self, state: dict, week_of_year: int) -> pd.DataFrame:
        return pd.DataFrame([{
            "lag_1": state["lag_1"], "lag_2": state["lag_2"], "lag_4": state["lag_4"],
            "rolling_mean_4": state["rolling_mean_4"],
            "week_of_year_sin": np.sin(2 * np.pi * week_of_year / 52),
            "week_of_year_cos": np.cos(2 * np.pi * week_of_year / 52),
        }])[self.feature_columns]

    def forecast(self, granularity: Granularity = "weekly") -> dict:
        from datetime import date
        week_of_year = date.today().isocalendar()[1]
        multiplier = MULTIPLIER[granularity]

        rev_row = self._row(self.meta["latest_revenue_state"], week_of_year)
        weekly_revenue = max(0.0, float(self.revenue_model.predict(rev_row)[0]))
        # Profit is derived from revenue x the historical average margin
        # rather than a fully independent model - training revenue and
        # profit as separate unconstrained forecasts let them drift out of
        # sync (a >80% implied margin at one point, vs ~45% historically),
        # so anchoring profit to revenue keeps the two internally consistent.
        weekly_profit = weekly_revenue * self.meta["historical_avg_margin"]

        return {
            "granularity": granularity,
            "forecasted_revenue": round(weekly_revenue * multiplier, 2),
            "forecasted_profit": round(weekly_profit * multiplier, 2),
            "forecasted_utilization": round(self.meta["latest_utilization_proxy"], 3),
            "model_version": self.meta["model_version"],
            "model_name": "revenue_forecast",
        }


if __name__ == "__main__":
    predictor = RevenuePredictor()
    for g in ["weekly", "monthly", "quarterly"]:
        print(f"{g} forecast ->", predictor.forecast(granularity=g))
