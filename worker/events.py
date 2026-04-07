"""Serving event FSM: zone + person proximity + dwell time."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from worker.geometry import any_person_near_plate, bbox_center_norm, point_in_polygon


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def wall_to_dt(t_wall: float) -> datetime:
    return datetime.fromtimestamp(t_wall, tz=timezone.utc)


@dataclass
class ZoneSpec:
    zone_id: uuid.UUID
    points: list[list[float]]


@dataclass
class TrackState:
    zone_enter_wall: float | None = None
    qualified: bool = False


@dataclass
class PendingEvent:
    camera_id: uuid.UUID
    plate_track_id: int
    started_at: datetime
    ended_at: datetime
    dwell_ms: int
    bbox_snapshot: dict
    confidence_avg: float


class ServingEventEngine:
    def __init__(
        self,
        camera_id: uuid.UUID,
        zones: list[ZoneSpec],
        dwell_seconds: float,
        require_person_near_plate: bool = True,
    ) -> None:
        self.camera_id = camera_id
        self.zones = zones
        self.dwell_seconds = dwell_seconds
        self.require_person_near_plate = require_person_near_plate
        self._states: dict[int, TrackState] = {}

    def process_frame(
        self,
        frame_w: int,
        frame_h: int,
        t_wall: float,
        plates: list,
        persons: list,
    ) -> list[PendingEvent]:
        """Update FSM; return completed serving events to persist."""
        completed: list[PendingEvent] = []
        person_boxes = [p.xyxy for p in persons]
        active_tracks: set[int] = set()

        for pl in plates:
            tid = pl.track_id
            active_tracks.add(tid)
            cx, cy = bbox_center_norm(pl.xyxy, frame_w, frame_h)
            in_any = False
            for z in self.zones:
                if point_in_polygon(cx, cy, z.points):
                    in_any = True
                    break
            if not self.zones:
                in_any = True

            if self.require_person_near_plate:
                person_ok = bool(person_boxes) and any_person_near_plate(pl.xyxy, person_boxes)
            else:
                person_ok = True
            st = self._states.setdefault(tid, TrackState())
            good = in_any and person_ok

            if good:
                if st.zone_enter_wall is None:
                    st.zone_enter_wall = t_wall
                if not st.qualified and st.zone_enter_wall is not None:
                    if (t_wall - st.zone_enter_wall) >= self.dwell_seconds:
                        st.qualified = True
            else:
                if st.qualified and st.zone_enter_wall is not None:
                    dwell_ms = int((t_wall - st.zone_enter_wall) * 1000)
                    completed.append(
                        PendingEvent(
                            camera_id=self.camera_id,
                            plate_track_id=tid,
                            started_at=wall_to_dt(st.zone_enter_wall),
                            ended_at=wall_to_dt(t_wall),
                            dwell_ms=dwell_ms,
                            bbox_snapshot={
                                "xyxy": list(pl.xyxy),
                                "frame_w": frame_w,
                                "frame_h": frame_h,
                            },
                            confidence_avg=pl.conf,
                        )
                    )
                st.zone_enter_wall = None
                st.qualified = False

        for tid in list(self._states.keys()):
            if tid not in active_tracks:
                st = self._states[tid]
                if st.qualified and st.zone_enter_wall is not None:
                    dwell_ms = int((t_wall - st.zone_enter_wall) * 1000)
                    completed.append(
                        PendingEvent(
                            camera_id=self.camera_id,
                            plate_track_id=tid,
                            started_at=wall_to_dt(st.zone_enter_wall),
                            ended_at=wall_to_dt(t_wall),
                            dwell_ms=dwell_ms,
                            bbox_snapshot={"lost_track": True},
                            confidence_avg=0.0,
                        )
                    )
                del self._states[tid]

        return completed
