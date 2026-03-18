from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from models import UserRole, AlertType


class RoadSegmentCreate(BaseModel):
    name: str
    geometry: str
    max_speed: int = Field(gt=0)
    length_meters: float = Field(gt=0)


class RoadSegmentRead(BaseModel):
    id: int
    name: str
    geometry: str
    max_speed: int
    length_meters: float
    last_updated: datetime

    class Config:
        from_attributes = True


class TrafficFlowCreate(BaseModel):
    segment_id: int
    timestamp: datetime
    average_speed: float
    vehicle_count: int
    occupancy: float = Field(ge=0, le=100)
    flow_direction: str


class TrafficFlowRead(BaseModel):
    id: int
    segment_id: int
    timestamp: datetime
    average_speed: float
    vehicle_count: int
    occupancy: float
    flow_direction: str

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    segment_id: int
    type: AlertType
    severity: int = Field(ge=1, le=5)
    description: Optional[str] = None


class AlertRead(BaseModel):
    id: int
    segment_id: int
    type: AlertType
    severity: int
    timestamp: datetime
    description: Optional[str]
    is_resolved: bool
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlertResolve(BaseModel):
    resolved: bool = True


class AnalyticsMetricRead(BaseModel):
    id: int
    segment_id: int
    time_window: str
    period_start: datetime
    period_end: datetime
    average_flow: float
    congestion_index: float
    mean_delay_minutes: float

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole

    class Config:
        from_attributes = True


class TrafficSnapshot(BaseModel):
    segment: RoadSegmentRead
    latest_flow: Optional[TrafficFlowRead]
    congestion_index: float
    has_active_alert: bool


class TrafficIngestBatch(BaseModel):
    items: List[TrafficFlowCreate]

