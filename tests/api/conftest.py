from __future__ import annotations

import pytest_asyncio
from anomaly_api.main import app
from anomaly_core.db import Base, SessionLocal, engine
from anomaly_core.rbac import ensure_default_rbac
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await ensure_default_rbac(session)
        await session.commit()
    yield


@pytest_asyncio.fixture
async def reset_db():
    async with SessionLocal() as session:
        from sqlalchemy import text

        tables = [
            "audit_logs",
            "evidence",
            "findings",
            "runs",
            "refresh_tokens",
            "api_keys",
            "playbook_steps",
            "playbooks",
            "tags",
            "targets",
            "scope_entries",
            "scopes",
            "engagement_members",
            "engagements",
            "users",
            "role_permissions",
            "user_roles",
        ]
        for table in tables:
            await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        await ensure_default_rbac(session)
        await session.commit()
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
