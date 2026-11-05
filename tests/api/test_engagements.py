import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from anomaly_api.deps import get_db
from anomaly_api.main import app
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models.engagement import Engagement, EngagementMember, EngagementMode
from anomaly_core.models.user import Role, RoleName, User, UserRole


async def _admin(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.ADMIN))
    if role is None:
        role = Role(name=RoleName.ADMIN)
        db_session.add(role)
        await db_session.flush()
    user = User(email=f"admin-eng-{id(db_session)}@x.com", name="Admin", password_hash=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    await db_session.commit()
    return user


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, ['admin'])}"}


def _override(db_session):
    async def override_get_db():
        yield db_session

    return override_get_db


@pytest.mark.asyncio
async def test_engagement_crud(db_session):
    admin = await _admin(db_session)
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            created = await ac.post(
                "/api/engagements",
                headers=_headers(admin),
                json={"name": "Eng1", "mode": "own_infra"},
            )
            assert created.status_code == 201
            eid = created.json()["id"]

            listed = await ac.get("/api/engagements", headers=_headers(admin))
            assert listed.status_code == 200
            assert any(e["id"] == eid for e in listed.json())

            got = await ac.get(f"/api/engagements/{eid}", headers=_headers(admin))
            assert got.status_code == 200

            patched = await ac.patch(
                f"/api/engagements/{eid}", headers=_headers(admin), json={"name": "Eng1b"}
            )
            assert patched.status_code == 200
            assert patched.json()["name"] == "Eng1b"

            deleted = await ac.delete(f"/api/engagements/{eid}", headers=_headers(admin))
            assert deleted.status_code in (200, 204)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scope_and_target_management(db_session):
    admin = await _admin(db_session)
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            created = await ac.post(
                "/api/engagements",
                headers=_headers(admin),
                json={"name": "Eng2", "mode": "bug_bounty"},
            )
            eid = created.json()["id"]
            put_scope = await ac.put(
                f"/api/engagements/{eid}/scope",
                headers=_headers(admin),
                json={"notes": "n", "in_scope": ["example.com"], "out_of_scope": ["bad.com"]},
            )
            assert put_scope.status_code == 200
            get_scope = await ac.get(f"/api/engagements/{eid}/scope", headers=_headers(admin))
            assert get_scope.status_code == 200
            data = get_scope.json()
            assert "example.com" in data.get("in_scope", [])
            tgt = await ac.post(
                f"/api/engagements/{eid}/targets",
                headers=_headers(admin),
                json={"value": "example.com", "type": "domain"},
            )
            assert tgt.status_code in (200, 201)
    finally:
        app.dependency_overrides.clear()
