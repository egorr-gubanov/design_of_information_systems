from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlmodel import select

from db import get_session
from models import RoadSegment, TrafficFlow
from services_analytics import ingest_traffic_batch


def _geojson_line_string(coords_lng_lat: list[list[float]]) -> str:
    """Return GeoJSON LineString as JSON string for storage in `RoadSegment.geometry`."""
    return json.dumps({"type": "LineString", "coordinates": coords_lng_lat}, ensure_ascii=False)


def ensure_seeded() -> None:
    """Insert demo segments and traffic if the database is empty."""
    with get_session() as session:
        has_any_segment = session.exec(select(RoadSegment)).first() is not None
        if has_any_segment:
            return

        segments = [
            RoadSegment(
                name="Ленинский проспект (участок 1)",
                geometry=_geojson_line_string([[30.33, 59.93], [30.34, 59.934], [30.35, 59.938]]),
                max_speed=60,
                length_meters=2500,
            ),
            RoadSegment(
                name="Невский проспект (участок 2)",
                geometry=_geojson_line_string([[30.40, 59.93], [30.405, 59.936], [30.41, 59.942]]),
                max_speed=70,
                length_meters=2200,
            ),
            RoadSegment(
                name="Московский проспект (участок 3)",
                geometry=_geojson_line_string([[30.35, 59.90], [30.36, 59.905], [30.38, 59.912]]),
                max_speed=80,
                length_meters=2800,
            ),
        ]

        session.add_all(segments)
        session.commit()
        for s in segments:
            session.refresh(s)

        segment_ids = [s.id for s in segments if s.id is not None]
        if not segment_ids:
            return

    now = datetime.utcnow()
    # Create flows so that congestion_index is high (low speed + high occupancy).
    flows: list[TrafficFlow] = []
    for seg_id in segment_ids:
        flows.append(
            TrafficFlow(
                segment_id=seg_id,
                timestamp=now - timedelta(minutes=12),
                average_speed=15.0,
                vehicle_count=120,
                occupancy=85.0,
                flow_direction="N",
            )
        )
        flows.append(
            TrafficFlow(
                segment_id=seg_id,
                timestamp=now - timedelta(minutes=7),
                average_speed=18.0,
                vehicle_count=105,
                occupancy=78.0,
                flow_direction="N",
            )
        )

    ingest_traffic_batch(flows)

