from __future__ import annotations

import pytest_asyncio
from anomaly_api.main import app
from anomaly_core.db import Base, engine
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client(reset_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
