from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Tuple

from sqlmodel import select

from db import get_session
from models import TrafficFlow, AnalyticsMetric, RoadSegment, Alert, AlertType


def calculate_congestion_index(average_speed: float, occupancy: float, max_speed: int) -> float:
    """Simple heuristic congestion index 0-100 based on speed and occupancy."""
    if max_speed <= 0:
        return 0.0
    speed_ratio = max(0.0, min(1.0, average_speed / max_speed))
    occupancy_ratio = max(0.0, min(1.0, occupancy / 100.0))
    # Higher occupancy and lower speed increase congestion
    raw = (1.0 - speed_ratio) * 0.6 + occupancy_ratio * 0.4
    return max(0.0, min(100.0, raw * 100.0))


def ingest_traffic_batch(flows: Iterable[TrafficFlow]) -> None:
    """Persist a batch of traffic flows and update analytics/alerts."""
    with get_session() as session:
        for flow in flows:
            session.add(flow)
        session.commit()

        # For simplicity, recompute metrics for last hour per affected segment
        segment_ids = {flow.segment_id for flow in flows}
        for segment_id in segment_ids:
            _recompute_recent_metrics_for_segment(session, segment_id)

        session.commit()


def _recompute_recent_metrics_for_segment(session, segment_id: int) -> None:
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    stmt = (
        select(TrafficFlow)
        .where(TrafficFlow.segment_id == segment_id)
        .where(TrafficFlow.timestamp >= one_hour_ago)
    )
    flows = session.exec(stmt).all()
    if not flows:
        return

    segment = session.get(RoadSegment, segment_id)
    if not segment:
        return

    avg_speed = sum(f.average_speed for f in flows) / len(flows)
    avg_occupancy = sum(f.occupancy for f in flows) / len(flows)
    avg_flow_rate = sum(f.vehicle_count for f in flows) / max(1, len(flows))

    congestion_index = calculate_congestion_index(
        average_speed=avg_speed,
        occupancy=avg_occupancy,
        max_speed=segment.max_speed,
    )

    metric = AnalyticsMetric(
        segment_id=segment_id,
        time_window="hourly",
        period_start=one_hour_ago,
        period_end=datetime.utcnow(),
        average_flow=avg_flow_rate,
        congestion_index=congestion_index,
        mean_delay_minutes=max(0.0, (1.0 - avg_speed / max(segment.max_speed, 1)) * 10.0),
    )
    session.add(metric)

    _maybe_create_congestion_alert(session, segment_id, congestion_index, avg_speed)


def _maybe_create_congestion_alert(
    session,
    segment_id: int,
    congestion_index: float,
    avg_speed: float,
) -> None:
    """Create a congestion alert if thresholds are exceeded."""
    if congestion_index < 70.0 and avg_speed > 20.0:
        return

    existing_active = session.exec(
        select(Alert).where(
            Alert.segment_id == segment_id,
            Alert.is_resolved == False,  # noqa: E712
            Alert.type == AlertType.CONGESTION,
        )
    ).first()
    if existing_active:
        return

    alert = Alert(
        segment_id=segment_id,
        type=AlertType.CONGESTION,
        severity=4 if congestion_index > 85 else 3,
        description=f"Высокая загруженность: индекс={congestion_index:.1f}, скорость={avg_speed:.1f} км/ч",
    )
    session.add(alert)


def get_latest_flow_and_index_for_segment(segment_id: int) -> Tuple[TrafficFlow | None, float]:
    """Return latest flow and congestion index based on latest hourly metric, if exists."""
    with get_session() as session:
        latest_flow = session.exec(
            select(TrafficFlow)
            .where(TrafficFlow.segment_id == segment_id)
            .order_by(TrafficFlow.timestamp.desc())
        ).first()

        latest_metric = session.exec(
            select(AnalyticsMetric)
            .where(AnalyticsMetric.segment_id == segment_id)
            .order_by(AnalyticsMetric.period_end.desc())
        ).first()

        congestion_index = latest_metric.congestion_index if latest_metric else 0.0
        return latest_flow, congestion_index

