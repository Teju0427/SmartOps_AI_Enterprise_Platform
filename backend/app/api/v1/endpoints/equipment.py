from __future__ import annotations

import math
import sys
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PaginationParams
from app.db.session import get_db
from app.models.equipment import Equipment, EquipmentStatus, RentalAvailability
from app.schemas.equipment import (
    EquipmentDetail,
    EquipmentPredictionsResponse,
    EquipmentRead,
    PaginatedEquipment,
)

sys.path.insert(0, "/app/ml")
from inference.predict_failure import FailurePredictor  # noqa: E402
from inference.predict_health import HealthPredictor  # noqa: E402
from inference.predict_rul import RULPredictor  # noqa: E402

router = APIRouter(prefix="/equipment", tags=["equipment"])

# Models are loaded once at import time (not per-request) - joblib
# deserialization takes tens of milliseconds and there's no reason to pay
# that cost on every API call.
_failure_predictor: FailurePredictor | None = None
_health_predictor: HealthPredictor | None = None
_rul_predictor: RULPredictor | None = None


def _get_predictors() -> tuple[FailurePredictor, HealthPredictor, RULPredictor]:
    global _failure_predictor, _health_predictor, _rul_predictor
    if _failure_predictor is None:
        _failure_predictor = FailurePredictor()
        _health_predictor = HealthPredictor()
        _rul_predictor = RULPredictor()
    return _failure_predictor, _health_predictor, _rul_predictor


def _sensor_payload(eq: Equipment) -> dict:
    if eq.base_daily_rate >= 900:
        ai4i_type = "H"
    elif eq.base_daily_rate >= 350:
        ai4i_type = "M"
    else:
        ai4i_type = "L"
    return {
        "type": ai4i_type,
        "air_temperature_k": eq.air_temperature_k or 298.0,
        "process_temperature_k": eq.process_temperature_k or 308.0,
        "rotational_speed_rpm": eq.rotational_speed_rpm or 1500.0,
        "torque_nm": eq.torque_nm or 40.0,
        "tool_wear_min": eq.tool_wear_min or 0.0,
    }


@router.get("", response_model=PaginatedEquipment)
def list_equipment(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[EquipmentStatus | None, Query(alias="status")] = None,
    availability: RentalAvailability | None = None,
    region: str | None = None,
    equipment_type: str | None = None,
    search: str | None = None,
) -> PaginatedEquipment:
    query = db.query(Equipment).filter(Equipment.is_deleted.is_(False))

    if status_filter:
        query = query.filter(Equipment.status == status_filter)
    if availability:
        query = query.filter(Equipment.availability == availability)
    if region:
        query = query.filter(Equipment.current_region == region)
    if equipment_type:
        query = query.filter(Equipment.equipment_type == equipment_type)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Equipment.name.ilike(like)) | (Equipment.asset_tag.ilike(like)) | (Equipment.machine_id.ilike(like))
        )

    total = query.count()
    items = (
        query.order_by(Equipment.health_score.asc().nulls_last())
        .offset(pagination.offset).limit(pagination.page_size).all()
    )

    return PaginatedEquipment(
        items=[EquipmentRead.model_validate(i) for i in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=max(1, math.ceil(total / pagination.page_size)),
    )


@router.get("/meta/regions", response_model=list[str])
def list_regions(db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> list[str]:
    rows = db.query(Equipment.current_region).distinct().all()
    return sorted(r[0] for r in rows)


@router.get("/meta/types", response_model=list[str])
def list_equipment_types(db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> list[str]:
    rows = db.query(Equipment.equipment_type).distinct().all()
    return sorted(r[0].value if hasattr(r[0], "value") else r[0] for r in rows)


@router.get("/{equipment_id}", response_model=EquipmentDetail)
def get_equipment(equipment_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> Equipment:
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if eq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
    return eq


@router.get("/{equipment_id}/predictions", response_model=EquipmentPredictionsResponse)
def get_equipment_predictions(
    equipment_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser,
) -> EquipmentPredictionsResponse:
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if eq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")

    failure_predictor, health_predictor, rul_predictor = _get_predictors()
    payload = _sensor_payload(eq)

    return EquipmentPredictionsResponse(
        equipment_id=eq.id,
        failure_prediction=failure_predictor.predict(payload),
        health=health_predictor.predict(payload),
        remaining_useful_life=rul_predictor.predict(payload),
    )
