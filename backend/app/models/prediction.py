"""
Prediction model.

Single polymorphic table storing every ML inference the platform makes
(price, failure, RUL, health, demand, revenue, CLV, ...). Storing all
predictions in one audited table - rather than one table per model -
makes it trivial to build a unified "Prediction Explorer" screen, track
model drift over time, and join predictions back to the AI Decision
Engine's recommendations regardless of which model produced them.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class PredictionType(str, enum.Enum):
    PRICE_PREDICTION = "price_prediction"
    FAILURE_PREDICTION = "failure_prediction"
    REMAINING_USEFUL_LIFE = "remaining_useful_life"
    HEALTH_SCORE = "health_score"
    MAINTENANCE_RECOMMENDATION = "maintenance_recommendation"
    DEMAND_FORECAST = "demand_forecast"
    REVENUE_FORECAST = "revenue_forecast"
    CUSTOMER_LTV = "customer_ltv"
    LATE_PAYMENT_RISK = "late_payment_risk"
    INVENTORY_RECOMMENDATION = "inventory_recommendation"
    AI_DECISION = "ai_decision"


class Prediction(UUIDPrimaryKeyMixin, Base):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    prediction_type: Mapped[PredictionType] = mapped_column(
        Enum(PredictionType, name="prediction_type_enum"), nullable=False, index=True
    )

    # Nullable FKs - a prediction may relate to equipment, a customer, both, or neither
    # (e.g. a region-level demand forecast has no single equipment/customer).
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"), nullable=True, index=True
    )

    model_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    # Core output - kept generic (JSON) since every prediction type has a
    # different output shape (price vs. RUL confidence interval vs. SHAP values).
    output_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_label: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. risk tier
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)  # full structured result
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    shap_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="predictions")
    customer: Mapped["Customer"] = relationship()
