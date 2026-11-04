import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from anomaly_core.db import Base
from anomaly_core.config import get_settings
from anomaly_core.models import User
from anomaly_core.auth import hash_password


@pytest_asyncio.fixture
async def db_session():
    settings = get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        from sqlalchemy import text
        tables = ["users"]
        for table in tables:
            await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        await session.commit()
    async with async_session() as test_session:
        yield test_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_simple(db_session):
    user = User(email="test@example.com", name="Test", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None
