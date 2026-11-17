from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_metrics_public_by_default(client, monkeypatch):
    monkeypatch.delenv("ANOMALY_METRICS_AUTH_REQUIRED", raising=False)
    r = await client.get("/api/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_requires_admin_when_configured(client, db_session, monkeypatch):
    monkeypatch.setenv("ANOMALY_METRICS_AUTH_REQUIRED", "1")

    # unauthenticated
    r = await client.get("/api/metrics")
    assert r.status_code == 401

    # non-admin
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if role is None:
        role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(role)
        await db_session.flush()
    user = User(
        email="metrics-user@example.com",
        name="U",
        password_hash=hash_password("pass"),
        roles=[role],
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(user.id, [RoleName.pentester.value])
    r = await client.get("/api/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403

    # admin allowed
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="metrics-admin@example.com",
        name="A",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(admin.id, [RoleName.admin.value])
    r = await client.get("/api/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
