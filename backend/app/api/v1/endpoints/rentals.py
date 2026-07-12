from __future__ import annotations

import math
import sys
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PaginationParams
from app.db.session import get_db
from app.models.rental import Rental, RentalStatus
from app.models.equipment import Equipment
from app.schemas.business import PaginatedRentals, RentalRead

sys.path.insert(0, "/app/ml")
from inference.predict_price import PricePredictor  # noqa: E402

router = APIRouter(prefix="/rentals", tags=["rentals"])

_price_predictor: PricePredictor | None = None


def _get_price_predictor() -> PricePredictor:
    global _price_predictor
    if _price_predictor is None:
        _price_predictor = PricePredictor()
    return _price_predictor


@router.get("", response_model=PaginatedRentals)
def list_rentals(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: Annotated[RentalStatus | None, Query(alias="status")] = None,
    equipment_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    region: str | None = None,
) -> PaginatedRentals:
    query = db.query(Rental)
    if status_filter:
        query = query.filter(Rental.status == status_filter)
    if equipment_id:
        query = query.filter(Rental.equipment_id == equipment_id)
    if customer_id:
        query = query.filter(Rental.customer_id == customer_id)
    if region:
        query = query.filter(Rental.region == region)

    total = query.count()
    items = query.order_by(Rental.start_date.desc()).offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedRentals(
        items=[RentalRead.model_validate(i) for i in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=max(1, math.ceil(total / pagination.page_size)),
    )


@router.get("/{rental_id}", response_model=RentalRead)
def get_rental(rental_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> Rental:
    rental = db.query(Rental).filter(Rental.id == rental_id).first()
    if rental is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental not found.")
    return rental


@router.post("/price-quote")
def get_price_quote(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    equipment_id: uuid.UUID,
    duration_days: int,
    customer_industry: str,
    competitor_price: float,
    inventory_count: int = 3,
    month: int = 7,
) -> dict:
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if eq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")

    predictor = _get_price_predictor()
    eq_type = eq.equipment_type.value if hasattr(eq.equipment_type, "value") else eq.equipment_type
    result = predictor.predict({
        "equipment_type": eq_type,
        "health_score": eq.health_score or 85.0,
        "market_competitor_price": competitor_price,
        "duration_days_planned": duration_days,
        "industry": customer_industry,
        "region": eq.current_region,
        "inventory_count": inventory_count,
        "month": month,
        "base_daily_rate": eq.base_daily_rate,
    })
    return result
