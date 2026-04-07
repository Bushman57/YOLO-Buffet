"""Async persistence for the worker."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.tables import (
    Camera,
    CameraHeartbeat,
    ModelVersion,
    PlateClassification,
    ServingEvent,
    ZoneDefinition,
)
from worker.events import PendingEvent, ZoneSpec


async def fetch_camera(session: AsyncSession, camera_id: uuid.UUID) -> Camera | None:
    return await session.get(Camera, camera_id)


async def fetch_zones(session: AsyncSession, camera_id: uuid.UUID) -> list[ZoneSpec]:
    q = await session.execute(
        select(ZoneDefinition).where(ZoneDefinition.camera_id == camera_id)
    )
    rows = q.scalars().all()
    out: list[ZoneSpec] = []
    for z in rows:
        geom = z.geometry or {}
        pts = geom.get("points") or []
        if isinstance(pts, list) and pts:
            out.append(ZoneSpec(zone_id=z.id, points=pts))
    return out


async def upsert_heartbeat(
    session: AsyncSession,
    camera_id: uuid.UUID,
    frame_count: int,
    last_seen_at: datetime,
    notes: str | None = None,
) -> None:
    hb = CameraHeartbeat(
        id=uuid.uuid4(),
        camera_id=camera_id,
        frame_count=frame_count,
        last_seen_at=last_seen_at,
        notes=notes,
    )
    session.add(hb)
    await session.commit()


async def insert_serving_event(session: AsyncSession, ev: PendingEvent) -> uuid.UUID:
    row = ServingEvent(
        id=uuid.uuid4(),
        camera_id=ev.camera_id,
        plate_track_id=ev.plate_track_id,
        started_at=ev.started_at,
        ended_at=ev.ended_at,
        dwell_ms=ev.dwell_ms,
        bbox_snapshot=ev.bbox_snapshot,
        confidence_avg=ev.confidence_avg,
    )
    session.add(row)
    await session.flush()
    return row.id


async def get_or_create_default_model_version(session: AsyncSession, name: str = "default") -> uuid.UUID:
    q = await session.execute(select(ModelVersion).where(ModelVersion.name == name).limit(1))
    mv = q.scalar_one_or_none()
    if mv:
        return mv.id
    mv = ModelVersion(id=uuid.uuid4(), name=name, path=None, metrics=None)
    session.add(mv)
    await session.commit()
    return mv.id


async def insert_classification(
    session: AsyncSession,
    serving_event_id: uuid.UUID,
    model_version_id: uuid.UUID,
    labels: dict,
) -> None:
    pc = PlateClassification(
        id=uuid.uuid4(),
        serving_event_id=serving_event_id,
        model_version_id=model_version_id,
        labels=labels,
    )
    session.add(pc)


async def commit_serving_event_and_classification(
    session: AsyncSession,
    ev: PendingEvent,
    model_version_id: uuid.UUID,
    labels: dict | None,
) -> uuid.UUID:
    eid = await insert_serving_event(session, ev)
    if labels is not None:
        await insert_classification(session, eid, model_version_id, labels)
    await session.commit()
    return eid
