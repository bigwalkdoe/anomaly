from __future__ import annotations

import pytest_asyncio
from anomaly_api.main import app
from anomaly_core.db import Base, SessionLocal, engine
from anomaly_core.rbac import ensure_default_rbac
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await ensure_default_rbac(session)
    yield


@pytest_asyncio.fixture
async def client(reset_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(reset_db):
    async with SessionLocal() as session:
        yield session
