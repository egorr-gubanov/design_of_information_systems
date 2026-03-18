from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session_dep
from models import Alert
from schemas import AlertCreate, AlertRead, AlertResolve


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertRead])
def list_alerts(only_active: bool = True, session: Session = Depends(get_session_dep)):
    query = select(Alert)
    if only_active:
        query = query.where(Alert.is_resolved == False)  # noqa: E712
    alerts = session.exec(query).all()
    return alerts


@router.post("/", response_model=AlertRead)
def create_alert(payload: AlertCreate, session: Session = Depends(get_session_dep)):
    alert = Alert(**payload.dict())
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(alert_id: int, body: AlertResolve, session: Session = Depends(get_session_dep)):
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if body.resolved and not alert.is_resolved:
        from datetime import datetime

        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        session.add(alert)
        session.commit()
        session.refresh(alert)
    return alert

