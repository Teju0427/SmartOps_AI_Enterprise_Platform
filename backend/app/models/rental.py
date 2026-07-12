"""
Rental transaction model - the fact table most BI/forecasting queries join against.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RentalStatus(str, enum.Enum):
    QUOTED = "quoted"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Rental(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    rental_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    status: Mapped[RentalStatus] = mapped_column(
        Enum(RentalStatus, name="rental_status_enum"),
        nullable=False,
        default=RentalStatus.QUOTED,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date_planned: Mapped[date] = mapped_column(Date, nullable=False)
    end_date_actual: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_days_planned: Mapped[int] = mapped_column(Integer, nullable=False)

    region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    pickup_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Pricing - both the AI-suggested price and what was actually charged
    # are stored so the pricing model's real-world accuracy can be tracked.
    market_competitor_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_suggested_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_price_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quoted_daily_rate: Mapped[float] = mapped_column(Float, nullable=False)
    final_daily_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_applied_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_profit: Mapped[float | None] = mapped_column(Float, nullable=True)

    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_late_payment: Mapped[bool] = mapped_column(default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="rentals")
    customer: Mapped["Customer"] = relationship(back_populates="rentals")
