from __future__ import annotations

import hashlib
import json
import pyotp
import pytest
from sqlalchemy import select

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import MFASecret, Role, RoleName, User


@pytest.mark.asyncio
async def test_mfa_setup_and_verify(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(email="mfa@example.com", name="MFA User", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Setup MFA
    resp = await client.post("/api/mfa/setup", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert "secret" in body
    assert "provisioning_uri" in body
    assert "backup_codes" in body
    assert len(body["backup_codes"]) == 8

    # Verify MFA status is not enabled yet
    resp = await client.get("/api/mfa/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False

    # Verify with TOTP
    totp = pyotp.TOTP(body["secret"])
    code = totp.now()
    resp = await client.post("/api/mfa/verify", headers=headers, json={"code": code})
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True

    # Verify status is now enabled
    resp = await client.get("/api/mfa/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_mfa_disable(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(email="mfa2@example.com", name="MFA User 2", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(user)
    await db_session.flush()

    # Setup and enable MFA with a valid TOTP secret
    import pyotp
    secret = pyotp.random_base32()
    import hashlib
    import json

    backup_codes = ["abcdefgh"]
    backup_codes_hash = json.dumps([hashlib.sha256(c.encode()).hexdigest() for c in backup_codes])
    mfa = MFASecret(
        user_id=user.id,
        secret_key=secret,
        is_enabled=True,
        backup_codes=backup_codes_hash,
    )
    db_session.add(mfa)
    await db_session.commit()

    token = create_access_token(user.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Disable with backup code
    resp = await client.post("/api/mfa/disable", headers=headers, json={"code": "abcdefgh"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json()["is_enabled"] is False

    # Verify disabled
    resp = await client.get("/api/mfa/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False


@pytest.mark.asyncio
async def test_mfa_login_flow(client, db_session):
    """Test login flow with MFA enabled."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(email="mfalogin@example.com", name="MFA Login", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(user)
    await db_session.flush()

    # Enable MFA
    import pyotp
    secret = pyotp.random_base32()
    mfa = MFASecret(
        user_id=user.id,
        secret_key=secret,
        is_enabled=True,
        backup_codes=None,
    )
    db_session.add(mfa)
    await db_session.commit()

    token = create_access_token(user.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Login should return mfa_required
    resp = await client.post(
        "/api/auth/login",
        json={"email": "mfalogin@example.com", "password": "pass"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mfa_required"] is True
    assert body["access_token"] is None

    # Verify with TOTP
    totp = pyotp.TOTP(mfa.secret_key)
    code = totp.now()
    resp = await client.post("/api/mfa/verify-login", headers=headers, json={"code": code})
    assert resp.status_code == 200
    assert resp.json()["verified"] is True
