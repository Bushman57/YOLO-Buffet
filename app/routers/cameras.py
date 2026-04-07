import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas import CameraOut, ZoneCreate, ZoneOut
from shared.models.tables import Camera, ZoneDefinition

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
async def list_cameras(
    site_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[Camera]:
    stmt = select(Camera)
    if site_id:
        stmt = stmt.where(Camera.site_id == site_id)
    stmt = stmt.order_by(Camera.name)
    q = await db.execute(stmt)
    return list(q.scalars().all())


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.get("/{camera_id}/zones", response_model=list[ZoneOut])
async def list_zones(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ZoneDefinition]:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    q = await db.execute(select(ZoneDefinition).where(ZoneDefinition.camera_id == camera_id))
    return list(q.scalars().all())


@router.post("/{camera_id}/zones", response_model=ZoneOut, status_code=201)
async def create_zone(
    camera_id: uuid.UUID,
    body: ZoneCreate,
    db: AsyncSession = Depends(get_db),
) -> ZoneDefinition:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    z = ZoneDefinition(
        id=uuid.uuid4(),
        camera_id=camera_id,
        zone_type=body.zone_type,
        geometry=body.geometry,
        meta=body.metadata,
    )
    db.add(z)
    await db.commit()
    await db.refresh(z)
    return z


@router.delete("/{camera_id}/zones/{zone_id}", status_code=204)
async def delete_zone(
    camera_id: uuid.UUID,
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    z = await db.get(ZoneDefinition, zone_id)
    if not z or z.camera_id != camera_id:
        raise HTTPException(status_code=404, detail="Zone not found")
    await db.delete(z)
    await db.commit()
    return Response(status_code=204)
