"""
Forecast, Alert, and Notification models.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


# ----------------------------------------------------------------------
# Forecast
# ----------------------------------------------------------------------
class ForecastGranularity(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ForecastMetric(str, enum.Enum):
    DEMAND = "demand"
    REVENUE = "revenue"
    PROFIT = "profit"
    UTILIZATION = "utilization"


class Forecast(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    metric: Mapped[ForecastMetric] = mapped_column(
        Enum(ForecastMetric, name="forecast_metric_enum"), nullable=False, index=True
    )
    granularity: Mapped[ForecastGranularity] = mapped_column(
        Enum(ForecastGranularity, name="forecast_granularity_enum"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    equipment_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)

    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # backfilled later

    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)


# ----------------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------------
class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    FAILURE_RISK = "failure_risk"
    MAINTENANCE_DUE = "maintenance_due"
    OVERDUE_RETURN = "overdue_return"
    LATE_PAYMENT = "late_payment"
    LOW_INVENTORY = "low_inventory"
    PRICE_ANOMALY = "price_anomaly"
    HEALTH_DEGRADATION = "health_degradation"


class Alert(UUIDPrimaryKeyMixin, Base):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type_enum"), nullable=False, index=True
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity_enum"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"), nullable=True, index=True
    )

    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="alerts")
    customer: Mapped["Customer"] = relationship()


# ----------------------------------------------------------------------
# Notifications (in-app delivery of alerts / system messages to users)
# ----------------------------------------------------------------------
class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class Notification(UUIDPrimaryKeyMixin, Base):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alert.id", ondelete="CASCADE"), nullable=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sent_successfully: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship()
    alert: Mapped["Alert"] = relationship()
