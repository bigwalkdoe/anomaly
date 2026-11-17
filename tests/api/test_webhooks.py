from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Role, RoleName, User
from sqlalchemy import select


async def _admin(db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="wh-admin@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.commit()
    return admin


async def _pentester(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if role is None:
        role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(role)
        await db_session.flush()
    user = User(
        email="wh-pentester@example.com",
        name="P",
        password_hash=hash_password("pass"),
        roles=[role],
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_webhooks_admin_only(client, db_session):
    user = await _pentester(db_session)
    token = create_access_token(user.id, ["pentester"])
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/webhooks", headers=headers)
    assert r.status_code == 403
    r = await client.post("/api/webhooks", headers=headers, json={"url": "https://x.test"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_webhooks_admin_list_and_create_not_implemented(client, db_session):
    admin = await _admin(db_session)
    token = create_access_token(admin.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/webhooks", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    r = await client.post("/api/webhooks", headers=headers, json={"url": "https://x.test"})
    assert r.status_code == 501
    body = r.json()
    # error handler formats as {"success": False, "error": ...}
    msg = ""
    if isinstance(body, dict):
        msg = str(body.get("detail") or body.get("error") or "")
    assert "not implemented" in msg.lower() or "not implemented" in r.text.lower()
