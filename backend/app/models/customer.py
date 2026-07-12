"""
Customer domain models - feeds Customer Intelligence module
(CLV, profitability, late-payment risk, discount recommendation).
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CustomerIndustry(str, enum.Enum):
    OIL_GAS = "oil_gas"
    CONSTRUCTION = "construction"
    MANUFACTURING = "manufacturing"
    MINING = "mining"
    UTILITIES = "utilities"
    CHEMICALS = "chemicals"
    AGRICULTURE = "agriculture"
    LOGISTICS = "logistics"
    EVENTS = "events"
    OTHER = "other"


class PaymentRiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[CustomerIndustry] = mapped_column(
        Enum(CustomerIndustry, name="customer_industry_enum"), nullable=False, index=True
    )
    region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    onboarded_date: Mapped[date] = mapped_column(Date, nullable=False)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Denormalized BI fields - refreshed nightly by the Customer
    # Intelligence pipeline; keeps dashboard queries index-only.
    lifetime_value: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    profitability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    late_payment_risk: Mapped[PaymentRiskTier | None] = mapped_column(
        Enum(PaymentRiskTier, name="payment_risk_tier_enum"), nullable=True, index=True
    )
    late_payment_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_equipment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_rentals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="customer")
