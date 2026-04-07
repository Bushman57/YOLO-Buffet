"""Create demo org / site / camera for local testing (requires DATABASE_URL)."""

from __future__ import annotations

import asyncio
import uuid

from shared.db.session import async_session_factory
from shared.models.tables import Camera, Organization, Site


async def main() -> None:
    oid = uuid.uuid4()
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    factory = async_session_factory()
    async with factory() as session:
        session.add(Organization(id=oid, name="Demo Org"))
        session.add(Site(id=sid, organization_id=oid, name="Demo Site"))
        session.add(
            Camera(
                id=cid,
                site_id=sid,
                name="Demo Camera",
                rtsp_url="rtsp://127.0.0.1:554/live",
                status="active",
                fps_target=5.0,
            )
        )
        await session.commit()
        print(f"Seeded organization={oid} site={sid} camera={cid}")


if __name__ == "__main__":
    asyncio.run(main())
