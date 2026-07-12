from __future__ import annotations

import math
import sys
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PaginationParams
from app.db.session import get_db
from app.models.customer import Customer, CustomerIndustry
from app.schemas.business import CustomerIntelligenceResponse, CustomerRead, PaginatedCustomers

sys.path.insert(0, "/app/ml")
from inference.predict_customer import CustomerIntelligencePredictor  # noqa: E402

router = APIRouter(prefix="/customers", tags=["customers"])

_customer_predictor: CustomerIntelligencePredictor | None = None


def _get_customer_predictor() -> CustomerIntelligencePredictor:
    global _customer_predictor
    if _customer_predictor is None:
        _customer_predictor = CustomerIntelligencePredictor()
    return _customer_predictor


@router.get("", response_model=PaginatedCustomers)
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    industry: CustomerIndustry | None = None,
    region: str | None = None,
    search: str | None = None,
) -> PaginatedCustomers:
    query = db.query(Customer).filter(Customer.is_deleted.is_(False))
    if industry:
        query = query.filter(Customer.industry == industry)
    if region:
        query = query.filter(Customer.region == region)
    if search:
        query = query.filter(Customer.company_name.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(Customer.total_revenue.desc()).offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedCustomers(
        items=[CustomerRead.model_validate(i) for i in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        total_pages=max(1, math.ceil(total / pagination.page_size)),
    )


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_deleted.is_(False)).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer


@router.get("/{customer_id}/intelligence", response_model=CustomerIntelligenceResponse)
def get_customer_intelligence(
    customer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)], current_user: CurrentUser,
) -> CustomerIntelligenceResponse:
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_deleted.is_(False)).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    predictor = _get_customer_predictor()
    industry_val = customer.industry.value if hasattr(customer.industry, "value") else customer.industry
    tenure_days = (datetime.now(timezone.utc).date() - customer.onboarded_date).days

    result = predictor.predict({
        "industry": industry_val,
        "region": customer.region,
        "credit_limit": customer.credit_limit,
        "tenure_days": tenure_days,
        "total_rentals": customer.total_rentals,
        "avg_discount_pct": 5.0,
        "avg_duration_days": 14.0,
    })

    return CustomerIntelligenceResponse(
        customer_id=customer.id,
        predicted_lifetime_value=result["predicted_lifetime_value"],
        late_payment_risk_probability=result["late_payment_risk_probability"],
        late_payment_risk_tier=result["late_payment_risk_tier"],
        recommended_discount_pct=result["recommended_discount_pct"],
    )
