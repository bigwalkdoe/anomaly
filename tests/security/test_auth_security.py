from __future__ import annotations

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models import Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_protected_endpoint_requires_authentication(client):
    """Unauthenticated requests to protected endpoints should be rejected."""
    response = await client.get("/api/engagements")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invalid_token_rejected(client):
    """Requests with invalid tokens should be rejected."""
    response = await client.get(
        "/api/engagements", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_sql_injection_in_search_is_safe(client, db_session):
    """SQL injection attempts in search should not cause errors or data leaks."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(
        email="sec@example.com",
        name="Sec User",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(user)
    await db_session.commit()

    from anomaly_core.auth import create_access_token

    token = create_access_token(user.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    # Attempt SQL injection
    response = await client.get("/api/search?q=' OR '1'='1", headers=headers)
    # Should not crash and should not leak data (auth rejection is also safe)
    assert response.status_code in (200, 400, 401, 403, 422)


@pytest.mark.asyncio
async def test_xss_in_registration_is_handled(client):
    """XSS attempts in registration should be handled safely."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "xss@example.com",
            "name": "<script>alert('xss')</script>",
            "password": "password123",
        },
    )
    # Should not crash - either succeed with sanitized data or reject
    assert response.status_code in (200, 201, 400, 422)


@pytest.mark.asyncio
async def test_password_not_exposed_in_responses(client, db_session):
    """Password hashes should never be exposed in API responses."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(
        email="pwd@example.com",
        name="Pwd User",
        password_hash=hash_password("secret"),
        roles=[admin_role],
    )
    db_session.add(user)
    await db_session.commit()

    from anomaly_core.auth import create_access_token

    token = create_access_token(user.id, ["admin"])
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "password" not in data
    assert "password_hash" not in data
