from __future__ import annotations

import pytest_asyncio
from anomaly_core.db import Base, SessionLocal, engine


@pytest_asyncio.fixture
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(reset_db):
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def session(db_session):
    yield db_session
