import pytest
from anomaly_api.deps import get_db
from anomaly_api.main import app
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models.engagement import Engagement, EngagementMember, EngagementMode
from anomaly_core.models.finding import Finding, FindingSeverity, FindingStatus
from anomaly_core.models.user import Role, RoleName, User, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _make_user(db_session, email: str, role_name: RoleName) -> User:
    role = await db_session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name)
        db_session.add(role)
        await db_session.flush()
    user = User(email=email, name=email.split("@")[0], password_hash=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


def _token(user: User, role: str) -> str:
    return create_access_token(user.id, roles=[role])


def _override(db_session):
    async def override_get_db():
        yield db_session

    return override_get_db


@pytest.mark.asyncio
async def test_admin_can_access_any_engagement(db_session):
    admin = await _make_user(db_session, "admin@x.com", RoleName.ADMIN)
    owner = await _make_user(db_session, "owner@x.com", RoleName.PENTESTER)
    eng = Engagement(name="E1", mode=EngagementMode.CLIENT, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/engagements/{eng.id}",
                headers={"Authorization": f"Bearer {_token(admin, 'admin')}"},
            )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pentester_can_access_assigned_only(db_session):
    pent = await _make_user(db_session, "pent@x.com", RoleName.PENTESTER)
    other = await _make_user(db_session, "other@x.com", RoleName.PENTESTER)
    eng = Engagement(name="E2", mode=EngagementMode.OWN_INFRA, owner_id=pent.id)
    eng2 = Engagement(name="E3", mode=EngagementMode.OWN_INFRA, owner_id=other.id)
    db_session.add_all([eng, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=pent.id, role="pentester"))
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ok = await ac.get(
                f"/api/engagements/{eng.id}",
                headers={"Authorization": f"Bearer {_token(pent, 'pentester')}"},
            )
            denied = await ac.get(
                f"/api/engagements/{eng2.id}",
                headers={"Authorization": f"Bearer {_token(pent, 'pentester')}"},
            )
        assert ok.status_code == 200
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_client_viewer_read_only(db_session):
    client = await _make_user(db_session, "client@x.com", RoleName.CLIENT_VIEWER)
    owner = await _make_user(db_session, "own@x.com", RoleName.PENTESTER)
    eng = Engagement(name="E4", mode=EngagementMode.CLIENT, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=client.id, role="client_viewer"))
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        headers = {"Authorization": f"Bearer {_token(client, 'client_viewer')}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            findings = await ac.get(f"/api/engagements/{eng.id}/findings", headers=headers)
            run_resp = await ac.post(
                f"/api/engagements/{eng.id}/runs",
                headers=headers,
                json={"tool": "stub", "targets": ["x"]},
            )
        assert findings.status_code == 200
        assert run_resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unassigned_user_gets_403(db_session):
    user = await _make_user(db_session, "u@x.com", RoleName.PENTESTER)
    owner = await _make_user(db_session, "o@x.com", RoleName.PENTESTER)
    eng = Engagement(name="E5", mode=EngagementMode.CLIENT, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/engagements/{eng.id}",
                headers={"Authorization": f"Bearer {_token(user, 'pentester')}"},
            )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cross_engagement_finding_read_returns_404(db_session):
    user = await _make_user(db_session, "u2@x.com", RoleName.PENTESTER)
    owner = await _make_user(db_session, "o2@x.com", RoleName.PENTESTER)
    eng1 = Engagement(name="E6", mode=EngagementMode.CLIENT, owner_id=owner.id)
    eng2 = Engagement(name="E7", mode=EngagementMode.CLIENT, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=user.id, role="pentester"))
    finding = Finding(
        engagement_id=eng2.id,
        title="Secret",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.NEW,
        fingerprint="fp-rbac",
    )
    db_session.add(finding)
    await db_session.commit()

    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/findings/{finding.id}",
                headers={"Authorization": f"Bearer {_token(user, 'pentester')}"},
            )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
