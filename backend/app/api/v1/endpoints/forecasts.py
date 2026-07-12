from __future__ import annotations

import sys
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser

sys.path.insert(0, "/app/ml")
from inference.predict_demand import DemandPredictor  # noqa: E402
from inference.predict_revenue import RevenuePredictor  # noqa: E402

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

_demand_predictor: DemandPredictor | None = None
_revenue_predictor: RevenuePredictor | None = None


def _get_demand_predictor() -> DemandPredictor:
    global _demand_predictor
    if _demand_predictor is None:
        _demand_predictor = DemandPredictor()
    return _demand_predictor


def _get_revenue_predictor() -> RevenuePredictor:
    global _revenue_predictor
    if _revenue_predictor is None:
        _revenue_predictor = RevenuePredictor()
    return _revenue_predictor


@router.get("/demand")
def get_demand_forecast(
    current_user: CurrentUser,
    granularity: Literal["daily", "weekly", "monthly", "quarterly"] = "weekly",
    region: str | None = None,
) -> dict:
    predictor = _get_demand_predictor()
    return predictor.forecast(granularity=granularity, region=region)


@router.get("/demand/by-region")
def get_demand_forecast_all_regions(
    current_user: CurrentUser,
    granularity: Literal["daily", "weekly", "monthly", "quarterly"] = "weekly",
) -> list[dict]:
    predictor = _get_demand_predictor()
    return predictor.forecast_all_regions(granularity=granularity)


@router.get("/revenue")
def get_revenue_forecast(
    current_user: CurrentUser,
    granularity: Literal["weekly", "monthly", "quarterly"] = "weekly",
) -> dict:
    predictor = _get_revenue_predictor()
    return predictor.forecast(granularity=granularity)
