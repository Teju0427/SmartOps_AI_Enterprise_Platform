"""
Equipment domain models.

Equipment is the central entity the AI4I predictive-maintenance dataset
maps onto (via `machine_id`) and that every ML module (health, RUL,
failure, pricing) references.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EquipmentType(str, enum.Enum):
    COMPRESSOR = "compressor"
    GENERATOR = "generator"
    ANALYZER = "analyzer"
    PUMP = "pump"
    EXCAVATOR = "excavator"
    CRANE = "crane"
    FORKLIFT = "forklift"
    WELDING_MACHINE = "welding_machine"
    DRILLING_RIG = "drilling_rig"
    HVAC_UNIT = "hvac_unit"


class EquipmentStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class RentalAvailability(str, enum.Enum):
    AVAILABLE = "available"
    RENTED = "rented"
    IN_MAINTENANCE = "in_maintenance"
    RETIRED = "retired"
    IN_TRANSIT = "in_transit"


class Equipment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    machine_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    asset_tag: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_type: Mapped[EquipmentType] = mapped_column(
        Enum(EquipmentType, name="equipment_type_enum"), nullable=False, index=True
    )
    manufacturer: Mapped[str] = mapped_column(String(120), nullable=False)
    model_number: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI4I dataset process-parameter fields (kept native so raw sensor
    # snapshots can feed the ML models without a lossy round trip)
    air_temperature_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    process_temperature_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    rotational_speed_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_wear_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Current derived state (denormalized for fast dashboard reads;
    # source of truth is the Prediction table, refreshed by the ML pipeline)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus, name="equipment_status_enum"),
        nullable=False,
        default=EquipmentStatus.HEALTHY,
        index=True,
    )
    availability: Mapped[RentalAvailability] = mapped_column(
        Enum(RentalAvailability, name="rental_availability_enum"),
        nullable=False,
        default=RentalAvailability.AVAILABLE,
        index=True,
    )

    current_region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_daily_rate: Mapped[float] = mapped_column(Float, nullable=False)

    total_operating_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="equipment")
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="equipment"
    )
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="equipment")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="equipment")


class EquipmentHealthSnapshot(UUIDPrimaryKeyMixin, Base):
    """Time-series health readings - append-only, one row per scoring run.
    Kept separate from Equipment (which stores only the latest value) so
    the frontend can render health trend lines and RUL confidence bands."""

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus, name="equipment_status_enum"), nullable=False
    )
    failure_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    remaining_useful_life_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    rul_confidence_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    rul_confidence_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    equipment: Mapped["Equipment"] = relationship()
