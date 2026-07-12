from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.equipment import Equipment, EquipmentStatus, RentalAvailability
from app.models.rental import Rental, RentalStatus
from app.models.customer import Customer
from app.models.decision import DecisionRecommendation, RecommendationStatus
from app.models.forecast import Alert

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Annotated[Session, Depends(get_db)], current_user: CurrentUser) -> dict:
    total_equipment = db.query(func.count(Equipment.id)).filter(Equipment.is_deleted.is_(False)).scalar()
    available = db.query(func.count(Equipment.id)).filter(
        Equipment.is_deleted.is_(False), Equipment.availability == RentalAvailability.AVAILABLE
    ).scalar()
    critical_count = db.query(func.count(Equipment.id)).filter(
        Equipment.is_deleted.is_(False), Equipment.status == EquipmentStatus.CRITICAL
    ).scalar()
    warning_count = db.query(func.count(Equipment.id)).filter(
        Equipment.is_deleted.is_(False), Equipment.status == EquipmentStatus.WARNING
    ).scalar()
    avg_health = db.query(func.avg(Equipment.health_score)).filter(Equipment.is_deleted.is_(False)).scalar()

    total_revenue = db.query(func.sum(Rental.total_revenue)).filter(Rental.total_revenue.isnot(None)).scalar() or 0
    total_profit = db.query(func.sum(Rental.total_profit)).filter(Rental.total_profit.isnot(None)).scalar() or 0
    active_rentals = db.query(func.count(Rental.id)).filter(Rental.status == RentalStatus.ACTIVE).scalar()
    overdue_rentals = db.query(func.count(Rental.id)).filter(Rental.status == RentalStatus.OVERDUE).scalar()

    total_customers = db.query(func.count(Customer.id)).filter(Customer.is_deleted.is_(False)).scalar()
    top_customers = (
        db.query(Customer.company_name, Customer.total_revenue)
        .filter(Customer.is_deleted.is_(False)).order_by(Customer.total_revenue.desc()).limit(5).all()
    )

    pending_recommendations = db.query(func.count(DecisionRecommendation.id)).filter(
        DecisionRecommendation.status == RecommendationStatus.PENDING
    ).scalar()
    unresolved_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved.is_(False)).scalar()

    region_breakdown = (
        db.query(Equipment.current_region, func.count(Equipment.id))
        .filter(Equipment.is_deleted.is_(False)).group_by(Equipment.current_region).all()
    )

    return {
        "equipment": {
            "total": total_equipment, "available": available,
            "critical_count": critical_count, "warning_count": warning_count,
            "avg_health_score": round(float(avg_health), 1) if avg_health else None,
        },
        "financial": {
            "total_historical_revenue": round(float(total_revenue), 2),
            "total_historical_profit": round(float(total_profit), 2),
            "active_rentals": active_rentals, "overdue_rentals": overdue_rentals,
        },
        "customers": {
            "total": total_customers,
            "top_customers": [{"name": c[0], "revenue": round(float(c[1] or 0), 2)} for c in top_customers],
        },
        "alerts_and_decisions": {
            "pending_recommendations": pending_recommendations,
            "unresolved_alerts": unresolved_alerts,
        },
        "regional_breakdown": [{"region": r[0], "equipment_count": r[1]} for r in region_breakdown],
    }
