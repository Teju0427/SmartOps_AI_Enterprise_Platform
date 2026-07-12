from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.rental import RentalStatus
from app.models.customer import CustomerIndustry, PaymentRiskTier


class RentalRead(BaseModel):
    id: uuid.UUID
    rental_number: str
    equipment_id: uuid.UUID
    customer_id: uuid.UUID
    status: RentalStatus
    start_date: date
    end_date_planned: date
    end_date_actual: date | None
    duration_days_planned: int
    region: str
    quoted_daily_rate: float
    final_daily_rate: float | None
    total_revenue: float | None
    total_profit: float | None
    is_late_payment: bool

    model_config = {"from_attributes": True}


class PaginatedRentals(BaseModel):
    items: list[RentalRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class CustomerRead(BaseModel):
    id: uuid.UUID
    company_name: str
    industry: CustomerIndustry
    region: str
    contact_name: str
    contact_email: str
    onboarded_date: date
    credit_limit: float
    lifetime_value: float | None
    late_payment_risk: PaymentRiskTier | None
    total_rentals: int
    total_revenue: float

    model_config = {"from_attributes": True}


class PaginatedCustomers(BaseModel):
    items: list[CustomerRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class CustomerIntelligenceResponse(BaseModel):
    customer_id: uuid.UUID
    predicted_lifetime_value: float
    late_payment_risk_probability: float
    late_payment_risk_tier: str
    recommended_discount_pct: float
