import pytest
from anomaly_api.deps import get_db
from anomaly_api.main import app
from anomaly_core.audit import AuditService
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models.audit import AuditLog
from anomaly_core.models.engagement import (
    Engagement,
    EngagementMode,
)
from anomaly_core.models.user import Role, RoleName, User, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select


async def _admin(db_session):
    role = Role(name=RoleName.ADMIN)
    db_session.add(role)
    await db_session.flush()
    user = User(email="admin-audit@x.com", name="Admin", password_hash=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


def _override(db_session):
    async def override_get_db():
        yield db_session

    return override_get_db


@pytest.mark.asyncio
async def test_creating_engagement_writes_audit_row(db_session):
    admin = await _admin(db_session)
    await db_session.commit()
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/engagements",
                headers={"Authorization": f"Bearer {create_access_token(admin.id, ['admin'])}"},
                json={"name": "Audit Eng", "mode": "client"},
            )
        assert resp.status_code in (200, 201)
        count = await db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "engagement.create")
        )
        assert (count or 0) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scope_warning_writes_audit_row(db_session):
    await AuditService.log(
        db_session,
        actor_id=None,
        action="scope.warning",
        resource_type="run",
        resource_id=None,
        engagement_id=None,
        metadata={"target": "evil.com"},
    )
    await db_session.commit()
    row = await db_session.scalar(select(AuditLog).where(AuditLog.action == "scope.warning"))
    assert row is not None
    assert row.meta["target"] == "evil.com"


@pytest.mark.asyncio
async def test_audit_list_filters_and_respects_access(db_session):
    admin = await _admin(db_session)
    eng = Engagement(name="E-audit", mode=EngagementMode.CLIENT, owner_id=admin.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(AuditLog(action="a.one", resource_type="x", engagement_id=eng.id, meta={}))
    db_session.add(AuditLog(action="a.two", resource_type="x", engagement_id=None, meta={}))
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/audit?engagement_id={eng.id}",
                headers={"Authorization": f"Bearer {create_access_token(admin.id, ['admin'])}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        actions = [r["action"] for r in data]
        assert "a.one" in actions
        assert "a.two" not in actions
    finally:
        app.dependency_overrides.clear()
