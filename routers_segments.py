from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from db import get_session_dep
from models import RoadSegment
from schemas import RoadSegmentCreate, RoadSegmentRead

router = APIRouter(prefix="/api/segments", tags=["segments"])


@router.get("/", response_model=List[RoadSegmentRead])
def list_segments(session=Depends(get_session_dep)):
    segments = session.exec(select(RoadSegment)).all()
    return segments


@router.post("/", response_model=RoadSegmentRead)
def create_segment(payload: RoadSegmentCreate, session=Depends(get_session_dep)):
    segment = RoadSegment(**payload.dict())
    session.add(segment)
    session.commit()
    session.refresh(segment)
    return segment


@router.get("/{segment_id}", response_model=RoadSegmentRead)
def get_segment(segment_id: int, session=Depends(get_session_dep)):
    segment = session.get(RoadSegment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.delete("/{segment_id}", status_code=204)
def delete_segment(segment_id: int, session=Depends(get_session_dep)):
    segment = session.get(RoadSegment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    session.delete(segment)
    session.commit()
    return None

