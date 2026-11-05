import pytest
from anomaly_api.deps import get_db
from anomaly_api.main import app
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models.engagement import Engagement
from anomaly_core.models.user import Role, RoleName, User, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _admin(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.ADMIN))
    if role is None:
        role = Role(name=RoleName.ADMIN)
        db_session.add(role)
        await db_session.flush()
    user = User(
        email=f"admin-find-{id(db_session)}@x.com", name="Admin", password_hash=hash_password("pw")
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    eng = Engagement(name="FindEng", mode="client", owner_id=user.id)
    # mode is enum; easier to use model default via proper enum
    from anomaly_core.models.engagement import EngagementMode

    eng.mode = EngagementMode.CLIENT
    db_session.add(eng)
    await db_session.flush()
    await db_session.commit()
    return user, eng


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, ['admin'])}"}


def _override(db_session):
    async def override_get_db():
        yield db_session

    return override_get_db


@pytest.mark.asyncio
async def test_finding_crud_and_status_transition(db_session):
    admin, eng = await _admin(db_session)
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            created = await ac.post(
                f"/api/engagements/{eng.id}/findings",
                headers=_headers(admin),
                json={"title": "F1", "severity": "high", "description": "d"},
            )
            assert created.status_code == 201
            fid = created.json()["id"]

            listed = await ac.get(f"/api/engagements/{eng.id}/findings", headers=_headers(admin))
            assert listed.status_code == 200
            assert any(f["id"] == fid for f in listed.json())

            got = await ac.get(f"/api/findings/{fid}", headers=_headers(admin))
            assert got.status_code == 200

            patched = await ac.patch(
                f"/api/findings/{fid}", headers=_headers(admin), json={"title": "F1b"}
            )
            assert patched.status_code == 200

            transitioned = await ac.post(
                f"/api/findings/{fid}/status", headers=_headers(admin), json={"status": "triaged"}
            )
            assert transitioned.status_code == 200
            assert transitioned.json()["status"] == "triaged"

            deleted = await ac.delete(f"/api/findings/{fid}", headers=_headers(admin))
            assert deleted.status_code in (200, 204)
    finally:
        app.dependency_overrides.clear()
