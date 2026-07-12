"""
AI Decision Engine output - the synthesized, human-readable business
recommendations combining every upstream model's predictions
(e.g. "Increase rental price by 6%", "Move analyzer to Mumbai").
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class RecommendationCategory(str, enum.Enum):
    PRICING = "pricing"
    MAINTENANCE = "maintenance"
    INVENTORY_RELOCATION = "inventory_relocation"
    FLEET_REPLACEMENT = "fleet_replacement"
    CUSTOMER_RETENTION = "customer_retention"
    RISK_MITIGATION = "risk_mitigation"


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    EXPIRED = "expired"


class DecisionRecommendation(UUIDPrimaryKeyMixin, Base):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    category: Mapped[RecommendationCategory] = mapped_column(
        Enum(RecommendationCategory, name="recommendation_category_enum"),
        nullable=False,
        index=True,
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status_enum"),
        nullable=False,
        default=RecommendationStatus.PENDING,
        index=True,
    )

    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "Increase rental price by 6%"
    detailed_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Which upstream predictions were combined to produce this recommendation
    contributing_prediction_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of UUIDs

    estimated_impact_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g. $ impact
    estimated_impact_metric: Mapped[str | None] = mapped_column(String(64), nullable=True)  # "revenue", "cost_savings"
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)  # 0-100, ranks the feed
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    equipment: Mapped["Equipment"] = relationship()
    customer: Mapped["Customer"] = relationship()
