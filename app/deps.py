from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = async_session_factory()
    async with factory() as session:
        yield session
