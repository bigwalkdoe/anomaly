from __future__ import annotations

import pytest_asyncio
from anomaly_core.db import Base, SessionLocal, engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        from anomaly_core.rbac import ensure_default_rbac

        await ensure_default_rbac(session)
        await session.commit()
    yield


@pytest_asyncio.fixture
async def reset_db():
    async with SessionLocal() as session:
        from sqlalchemy import text

        tables = [
            "audit_logs", "evidence", "findings", "runs", "refresh_tokens",
            "api_keys", "playbook_steps", "playbooks", "tags", "targets",
            "scope_entries", "scopes", "engagement_members", "engagements",
            "users", "role_permissions",
        ]
        for table in tables:
            await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        # Don't truncate roles/permissions - they're needed by all tests
        from anomaly_core.rbac import ensure_default_rbac

        await ensure_default_rbac(session)
        await session.commit()
    yield


@pytest_asyncio.fixture
async def db_session(reset_db):
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def session(db_session):
    yield db_session
