"""
Maintenance models - predictive maintenance schedule, execution log, and cost tracking.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MaintenanceType(str, enum.Enum):
    PREVENTIVE = "preventive"
    PREDICTIVE = "predictive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"
    INSPECTION = "inspection"


class MaintenanceStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class MaintenanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, index=True
    )

    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType, name="maintenance_type_enum"), nullable=False, index=True
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(MaintenanceStatus, name="maintenance_status_enum"),
        nullable=False,
        default=MaintenanceStatus.SCHEDULED,
        index=True,
    )

    # AI-recommended fields (from Predictive Maintenance module)
    recommended_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Actuals
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    technician_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    parts_replaced: Mapped[str | None] = mapped_column(Text, nullable=True)
    downtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="maintenance_records")
