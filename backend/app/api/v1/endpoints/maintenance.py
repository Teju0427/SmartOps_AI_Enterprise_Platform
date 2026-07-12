from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PaginationParams
from app.db.session import get_db
from app.models.maintenance import MaintenanceRecord, MaintenanceStatus, MaintenanceType

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class MaintenanceRead(BaseModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    maintenance_type: MaintenanceType
    status: MaintenanceStatus
    recommended_date: date | None
    scheduled_date: date | None
    completed_date: date | None
    ai_estimated_cost: float | None
    actual_cost: float | None
    ai_reasoning: str | None

    model_config = {"from_attributes": True}


class PaginatedMaintenance(BaseModel):
    items: list[MaintenanceRead]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedMaintenance)
def list_maintenance(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[MaintenanceStatus | None, Query(alias="status")] = None,
    maintenance_type: MaintenanceType | None = None,
    equipment_id: uuid.UUID | None = None,
) -> PaginatedMaintenance:
    query = db.query(MaintenanceRecord)
    if status_filter:
        query = query.filter(MaintenanceRecord.status == status_filter)
    if maintenance_type:
        query = query.filter(MaintenanceRecord.maintenance_type == maintenance_type)
    if equipment_id:
        query = query.filter(MaintenanceRecord.equipment_id == equipment_id)

    total = query.count()
    items = (
        query.order_by(MaintenanceRecord.scheduled_date.desc().nulls_last())
        .offset(pagination.offset).limit(pagination.page_size).all()
    )

    return PaginatedMaintenance(
        items=[MaintenanceRead.model_validate(i) for i in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=max(1, math.ceil(total / pagination.page_size)),
    )


@router.get("/{maintenance_id}", response_model=MaintenanceRead)
def get_maintenance(maintenance_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> MaintenanceRecord:
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == maintenance_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found.")
    return record
