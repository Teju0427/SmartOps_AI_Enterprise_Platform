from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.equipment import EquipmentStatus, RentalAvailability


class EquipmentRead(BaseModel):
    id: uuid.UUID
    machine_id: str
    asset_tag: str
    name: str
    equipment_type: str
    manufacturer: str
    model_number: str
    health_score: float | None
    status: EquipmentStatus
    availability: RentalAvailability
    current_region: str
    base_daily_rate: float
    total_operating_hours: float
    purchase_date: date | None

    model_config = {"from_attributes": True}


class EquipmentDetail(EquipmentRead):
    air_temperature_k: float | None
    process_temperature_k: float | None
    rotational_speed_rpm: float | None
    torque_nm: float | None
    tool_wear_min: float | None
    purchase_cost: float | None
    current_location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedEquipment(BaseModel):
    items: list[EquipmentRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class EquipmentPredictionsResponse(BaseModel):
    equipment_id: uuid.UUID
    failure_prediction: dict
    health: dict
    remaining_useful_life: dict
