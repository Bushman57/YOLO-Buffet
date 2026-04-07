import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_db
from app.schemas import PaginatedEvents, ServingEventDetailOut, ServingEventOut
from shared.models.tables import Camera, ServingEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedEvents)
async def list_events(
    camera_id: uuid.UUID | None = Query(None),
    site_id: uuid.UUID | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEvents:
    id_stmt = select(ServingEvent.id)
    if camera_id:
        id_stmt = id_stmt.where(ServingEvent.camera_id == camera_id)
    elif site_id:
        id_stmt = id_stmt.join(Camera, ServingEvent.camera_id == Camera.id).where(
            Camera.site_id == site_id
        )
    if from_time:
        id_stmt = id_stmt.where(ServingEvent.started_at >= from_time)
    if to_time:
        id_stmt = id_stmt.where(ServingEvent.started_at <= to_time)

    subq = id_stmt.subquery()
    total = await db.scalar(select(func.count()).select_from(subq)) or 0

    stmt = select(ServingEvent)
    if camera_id:
        stmt = stmt.where(ServingEvent.camera_id == camera_id)
    elif site_id:
        stmt = stmt.join(Camera, ServingEvent.camera_id == Camera.id).where(
            Camera.site_id == site_id
        )
    if from_time:
        stmt = stmt.where(ServingEvent.started_at >= from_time)
    if to_time:
        stmt = stmt.where(ServingEvent.started_at <= to_time)

    stmt = stmt.order_by(ServingEvent.started_at.desc()).offset(offset).limit(limit)
    q = await db.execute(stmt)
    items = list(q.scalars().all())
    return PaginatedEvents(
        items=[ServingEventOut.model_validate(x) for x in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{event_id}", response_model=ServingEventDetailOut)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ServingEventDetailOut:
    q = await db.execute(
        select(ServingEvent)
        .where(ServingEvent.id == event_id)
        .options(selectinload(ServingEvent.classifications))
    )
    ev = q.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ServingEventDetailOut.model_validate(ev)
