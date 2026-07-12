from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PaginationParams
from app.db.session import get_db
from app.models.decision import DecisionRecommendation, RecommendationCategory, RecommendationStatus

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("")
def list_recommendations(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    category: RecommendationCategory | None = None,
    status_filter: Annotated[RecommendationStatus | None, Query(alias="status")] = None,
) -> dict:
    query = db.query(DecisionRecommendation)
    if category:
        query = query.filter(DecisionRecommendation.category == category)
    if status_filter:
        query = query.filter(DecisionRecommendation.status == status_filter)

    total = query.count()
    items = (
        query.order_by(DecisionRecommendation.priority_score.desc())
        .offset(pagination.offset).limit(pagination.page_size).all()
    )

    return {
        "items": [
            {
                "id": str(i.id), "category": i.category.value, "status": i.status.value,
                "title": i.title, "summary": i.summary, "detailed_reasoning": i.detailed_reasoning,
                "priority_score": i.priority_score, "confidence_score": i.confidence_score,
                "estimated_impact_value": i.estimated_impact_value,
                "estimated_impact_metric": i.estimated_impact_metric,
                "equipment_id": str(i.equipment_id) if i.equipment_id else None,
                "customer_id": str(i.customer_id) if i.customer_id else None,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
        "total": total, "page": pagination.page, "page_size": pagination.page_size,
        "total_pages": max(1, math.ceil(total / pagination.page_size)),
    }


@router.patch("/{recommendation_id}/status")
def update_recommendation_status(
    recommendation_id: uuid.UUID, new_status: RecommendationStatus,
    db: Annotated[Session, Depends(get_db)], current_user: CurrentUser,
) -> dict:
    rec = db.query(DecisionRecommendation).filter(DecisionRecommendation.id == recommendation_id).first()
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    rec.status = new_status
    rec.reviewed_by = current_user.id
    from datetime import datetime, timezone
    rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": str(rec.id), "status": rec.status.value}
