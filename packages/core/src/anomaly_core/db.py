from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from anomaly_core.config import get_settings
from anomaly_core.types import JSON, JSONType  # noqa: F401  (re-export for convenience)

settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
