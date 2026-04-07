import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas import OrganizationOut, SiteOut
from shared.models.tables import Organization, Site

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("/organizations", response_model=list[OrganizationOut])
async def list_organizations(db: AsyncSession = Depends(get_db)) -> list[Organization]:
    q = await db.execute(select(Organization).order_by(Organization.name))
    return list(q.scalars().all())


@router.get("", response_model=list[SiteOut])
async def list_sites(
    organization_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[Site]:
    stmt = select(Site)
    if organization_id:
        stmt = stmt.where(Site.organization_id == organization_id)
    stmt = stmt.order_by(Site.name)
    q = await db.execute(stmt)
    return list(q.scalars().all())


@router.get("/{site_id}/summary")
async def site_summary(
    site_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from fastapi import HTTPException

    from shared.models.tables import Camera

    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    nc = await db.scalar(select(func.count()).select_from(Camera).where(Camera.site_id == site_id))
    return {"site_id": str(site_id), "camera_count": nc or 0}
