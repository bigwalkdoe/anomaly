from __future__ import annotations

import pytest
from anomaly_api.routers.ws import notification_manager
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_notification_manager_broadcast(client, db_session):
    """Test notification manager broadcast_to_user directly."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(
        email="nm@example.com",
        name="NM User",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(user)
    await db_session.commit()

    user_id = str(user.id)

    # Test broadcast to user with no connections (should not error)
    await notification_manager.broadcast_to_user(user_id, {"type": "test", "message": "hello"})

    # Test broadcast_to_all with no connections
    await notification_manager.broadcast_to_all({"type": "test_all", "message": "hello all"})


@pytest.mark.asyncio
async def test_broadcast_notification_endpoint(client, db_session):
    """Test broadcast notification endpoint (admin only)."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(
        email="broadcast@example.com",
        name="Broadcast User",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/notifications/broadcast",
        headers=headers,
        json={"title": "Test Broadcast", "message": "Hello everyone", "severity": "info"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["broadcast"] is True


@pytest.mark.asyncio
async def test_broadcast_notification_non_admin(client, db_session):
    """Test that non-admin users cannot broadcast notifications."""
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
        await db_session.flush()
    user = User(
        email="nobroadcast@example.com",
        name="No Broadcast",
        password_hash=hash_password("pass"),
        roles=[pentester_role],
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id, ["pentester"])
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/notifications/broadcast",
        headers=headers,
        json={"title": "Test", "message": "Hello"},
    )
    assert resp.status_code == 403
