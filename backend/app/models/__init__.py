"""
Import every ORM model here so that:
1. `Base.metadata` is fully populated for Alembic autogenerate.
2. String-based relationship() references (e.g. "Equipment") resolve correctly
   regardless of which module is imported first.
"""
from app.db.base_class import Base  # noqa: F401

from app.models.user import User, RefreshToken, AuditLog, UserRole  # noqa: F401
from app.models.equipment import (  # noqa: F401
    Equipment,
    EquipmentHealthSnapshot,
    EquipmentType,
    EquipmentStatus,
    RentalAvailability,
)
from app.models.customer import Customer, CustomerIndustry, PaymentRiskTier  # noqa: F401
from app.models.rental import Rental, RentalStatus  # noqa: F401
from app.models.maintenance import (  # noqa: F401
    MaintenanceRecord,
    MaintenanceType,
    MaintenanceStatus,
)
from app.models.prediction import Prediction, PredictionType  # noqa: F401
from app.models.forecast import (  # noqa: F401
    Forecast,
    ForecastGranularity,
    ForecastMetric,
    Alert,
    AlertType,
    AlertSeverity,
    Notification,
    NotificationChannel,
)
from app.models.decision import (  # noqa: F401
    DecisionRecommendation,
    RecommendationCategory,
    RecommendationStatus,
)

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "AuditLog",
    "UserRole",
    "Equipment",
    "EquipmentHealthSnapshot",
    "EquipmentType",
    "EquipmentStatus",
    "RentalAvailability",
    "Customer",
    "CustomerIndustry",
    "PaymentRiskTier",
    "Rental",
    "RentalStatus",
    "MaintenanceRecord",
    "MaintenanceType",
    "MaintenanceStatus",
    "Prediction",
    "PredictionType",
    "Forecast",
    "ForecastGranularity",
    "ForecastMetric",
    "Alert",
    "AlertType",
    "AlertSeverity",
    "Notification",
    "NotificationChannel",
    "DecisionRecommendation",
    "RecommendationCategory",
    "RecommendationStatus",
]
