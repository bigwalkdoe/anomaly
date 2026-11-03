from __future__ import annotations

import pytest

REGISTER = {
    "email": "admin@example.com",
    "name": "Admin",
    "password": "correct-horse-battery",
}


async def _register(client, **overrides):
    payload = {**REGISTER, **overrides}
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_tokens(client):
    body = await _register(client)
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER["email"]
    assert me.json()["roles"] == ["admin"]


@pytest.mark.asyncio
async def test_login_with_correct_credentials(client):
    await _register(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(client):
    await _register(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": REGISTER["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_and_rejects_old_token(client):
    body = await _register(client)
    old_refresh = body["refresh_token"]

    rotated = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != old_refresh

    reused = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    body = await _register(client)
    refresh_token = body["refresh_token"]

    logout = await client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_second_registration_requires_admin(client):
    await _register(client)
    response = await client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "name": "Other", "password": "another-password"},
    )
    assert response.status_code == 403
