import pytest
from anomaly_api.deps import get_db
from anomaly_api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_tokens(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/auth/register",
                json={"email": "a@example.com", "name": "A", "password": "secret123"},
            )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_correct_creds_returns_tokens(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post(
                "/api/auth/register",
                json={"email": "b@example.com", "name": "B", "password": "secret123"},
            )
            resp = await ac.post(
                "/api/auth/login", json={"email": "b@example.com", "password": "secret123"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data and "refresh_token" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_wrong_creds_returns_401(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post(
                "/api/auth/register",
                json={"email": "c@example.com", "name": "C", "password": "secret123"},
            )
            resp = await ac.post(
                "/api/auth/login", json={"email": "c@example.com", "password": "wrong"}
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_with_access_token(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            reg = await ac.post(
                "/api/auth/register",
                json={"email": "d@example.com", "name": "D", "password": "secret123"},
            )
            token = reg.json()["access_token"]
            resp = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "d@example.com"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_without_token_returns_401(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/auth/me")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_refresh_rotates_and_rejects_old(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            reg = await ac.post(
                "/api/auth/register",
                json={"email": "e@example.com", "name": "E", "password": "secret123"},
            )
            old_refresh = reg.json()["refresh_token"]
            refreshed = await ac.post("/api/auth/refresh", json={"refresh_token": old_refresh})
            assert refreshed.status_code == 200
            assert refreshed.json()["refresh_token"] != old_refresh
            replay = await ac.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            reg = await ac.post(
                "/api/auth/register",
                json={"email": "f@example.com", "name": "F", "password": "secret123"},
            )
            tokens = reg.json()
            await ac.post(
                "/api/auth/logout",
                json={"refresh_token": tokens["refresh_token"]},
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            replay = await ac.post(
                "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            )
        assert replay.status_code == 401
    finally:
        app.dependency_overrides.clear()
