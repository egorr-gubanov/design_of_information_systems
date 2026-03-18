from datetime import datetime
from enum import Enum
from typing import List

from sqlmodel import SQLModel, Field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class AlertType(str, Enum):
    CONGESTION = "CONGESTION"
    ACCIDENT = "ACCIDENT"
    HAZARD = "HAZARD"


class RoadSegmentBase(SQLModel):
    name: str
    geometry: str  # GeoJSON or WKT string (simplified for prototype)
    max_speed: int
    length_meters: float


class RoadSegment(RoadSegmentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrafficFlowBase(SQLModel):
    timestamp: datetime
    average_speed: float
    vehicle_count: int
    occupancy: float  # percentage 0-100
    flow_direction: str


class TrafficFlow(TrafficFlowBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    segment_id: int = Field(foreign_key="roadsegment.id")


class AlertBase(SQLModel):
    type: AlertType
    severity: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: str | None = None
    is_resolved: bool = Field(default=False)
    resolved_at: datetime | None = None


class Alert(AlertBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    segment_id: int = Field(foreign_key="roadsegment.id")


class AnalyticsMetricBase(SQLModel):
    time_window: str  # e.g. "hourly", "daily"
    period_start: datetime
    period_end: datetime
    average_flow: float
    congestion_index: float  # 0-100
    mean_delay_minutes: float


class AnalyticsMetric(AnalyticsMetricBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    segment_id: int = Field(foreign_key="roadsegment.id")


class UserBase(SQLModel):
    name: str
    email: str
    role: UserRole = Field(default=UserRole.VIEWER)


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    department: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    is_active: bool = Field(default=True)

