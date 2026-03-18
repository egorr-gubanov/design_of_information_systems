from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from db import get_session_dep
from models import TrafficFlow, RoadSegment, Alert
from schemas import TrafficFlowCreate, TrafficFlowRead, TrafficIngestBatch, TrafficSnapshot
from services_analytics import ingest_traffic_batch, get_latest_flow_and_index_for_segment


router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.post("/ingest", status_code=204)
def ingest(batch: TrafficIngestBatch, session: Session = Depends(get_session_dep)):
    flows: List[TrafficFlow] = []
    for item in batch.items:
        flow = TrafficFlow(**item.dict())
        flows.append(flow)
    ingest_traffic_batch(flows)
    return None


@router.get("/current", response_model=List[TrafficSnapshot])
def current_traffic(session: Session = Depends(get_session_dep)):
    segments = session.exec(select(RoadSegment)).all()
    snapshots: List[TrafficSnapshot] = []
    for seg in segments:
        latest_flow, index = get_latest_flow_and_index_for_segment(seg.id)  # type: ignore[arg-type]
        has_alert = (
            session.exec(
                select(Alert).where(
                    Alert.segment_id == seg.id,
                    Alert.is_resolved == False,  # noqa: E712
                )
            ).first()
            is not None
        )
        snapshots.append(
            TrafficSnapshot(
                segment=seg,  # type: ignore[arg-type]
                latest_flow=latest_flow,
                congestion_index=index,
                has_active_alert=has_alert,
            )
        )
    return snapshots

