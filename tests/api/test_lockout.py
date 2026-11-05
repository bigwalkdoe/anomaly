from __future__ import annotations

import pytest
from sqlalchemy import select

from anomaly_core.auth import hash_password
from anomaly_core.models import LoginAttempt, Role, RoleName, User


@pytest.mark.asyncio
async def test_account_lockout_after_5_failures(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(email="lockout@example.com", name="Lockout User", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(user)
    await db_session.commit()

    # Make 5 failed login attempts
    for i in range(5):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "lockout@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    # 6th attempt should be locked out
    resp = await client.post(
        "/api/auth/login",
        json={"email": "lockout@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert "locked" in body.get("error", "").lower() or "locked" in body.get("detail", "").lower()


@pytest.mark.asyncio
async def test_successful_login_clears_lockout(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(email="clearlock@example.com", name="Clear Lock", password_hash=hash_password("correctpass"), roles=[admin_role])
    db_session.add(user)
    await db_session.commit()

    # Make 4 failed attempts
    for i in range(4):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "clearlock@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    # 5th attempt should still work (only 4 previous failures)
    resp = await client.post(
        "/api/auth/login",
        json={"email": "clearlock@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401

    # Now there are 5 failures - 6th attempt should lock out
    resp = await client.post(
        "/api/auth/login",
        json={"email": "clearlock@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 429

    # Now login with correct password - should clear lockout
    resp = await client.post(
        "/api/auth/login",
        json={"email": "clearlock@example.com", "password": "correctpass"},
    )
    # MFA is not enabled, so should get tokens
    assert resp.status_code == 200
    body = resp.json()
    assert body["mfa_required"] is False
    assert body["access_token"] is not None
