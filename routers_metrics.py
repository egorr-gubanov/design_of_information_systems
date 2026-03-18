from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from db import get_session_dep
from models import AnalyticsMetric
from schemas import AnalyticsMetricRead


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary", response_model=List[AnalyticsMetricRead])
def metrics_summary(limit: int = 50, session: Session = Depends(get_session_dep)):
    stmt = select(AnalyticsMetric).order_by(AnalyticsMetric.period_end.desc()).limit(limit)
    metrics = session.exec(stmt).all()
    return metrics

