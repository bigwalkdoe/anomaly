import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from anomaly_api.deps import get_db
from anomaly_api.main import app
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models.audit import AuditLog
from anomaly_core.models.engagement import Engagement, EngagementMember, EngagementMode, Scope, ScopeEntry
from anomaly_core.models.finding import Finding
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.models.user import Role, RoleName, User, UserRole
from anomaly_core.runner import FakeRunner, RunResult
from anomaly_worker.executor import execute_run_inline


async def _admin_eng(db_session, *, in_scope=None):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.ADMIN))
    if role is None:
        role = Role(name=RoleName.ADMIN)
        db_session.add(role)
        await db_session.flush()
    user = User(email=f"run-{uuid.uuid4().hex[:6]}@x.com", name="A", password_hash=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    eng = Engagement(name="RunEng", mode=EngagementMode.OWN_INFRA, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    for v in in_scope or []:
        db_session.add(ScopeEntry(scope_id=scope.id, kind="in", target_value=v))
    await db_session.commit()
    return user, eng


def _override(db_session):
    async def override_get_db():
        yield db_session
    return override_get_db


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, ['admin'])}"}


@pytest.mark.asyncio
async def test_enqueue_run_returns_202_and_writes_audit(db_session):
    user, eng = await _admin_eng(db_session, in_scope=["example.com"])
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/engagements/{eng.id}/runs",
                headers=_headers(user),
                json={"tool": "stub", "targets": ["example.com"]},
            )
        assert resp.status_code == 202
        run_id = resp.json()["id"]
        assert run_id
        count = await db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "run.enqueue")
        )
        assert (count or 0) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_out_of_scope_sets_scope_warning(db_session):
    user, eng = await _admin_eng(db_session, in_scope=["example.com"])
    app.dependency_overrides[get_db] = _override(db_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/engagements/{eng.id}/runs",
                headers=_headers(user),
                json={"tool": "stub", "targets": ["evil.com"]},
            )
        assert resp.status_code == 202
        run_id = resp.json()["id"]
        run = await db_session.get(Run, uuid.UUID(run_id))
        assert run is not None
        assert run.scope_warning is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_vertical_slice_stub_tool(db_session):
    user, eng = await _admin_eng(db_session, in_scope=["example.com"])
    from anomaly_core.audit import AuditService

    await AuditService.log(db_session, user.id, "engagement.create", "engagement", eng.id, eng.id, {})
    await AuditService.log(db_session, user.id, "run.enqueue", "run", None, eng.id, {})
    await AuditService.log(db_session, user.id, "scope.check", "run", None, eng.id, {})
    run = Run(
        engagement_id=eng.id,
        user_id=user.id,
        tool="stub",
        target_ids=[],
        params={"targets": ["example.com"]},
        status=RunStatus.QUEUED,
        scope_warning=False,
    )
    db_session.add(run)
    await db_session.commit()

    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout="stub", stderr="", artifacts=[], duration_s=0.1)
    )
    await execute_run_inline(db_session, run.id, runner=runner)

    await db_session.refresh(run)
    assert run.status == RunStatus.SUCCEEDED
    finding_count = await db_session.scalar(
        select(func.count()).select_from(Finding).where(Finding.engagement_id == eng.id)
    )
    assert (finding_count or 0) >= 1
    audit_count = await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.engagement_id == eng.id)
    )
    assert (audit_count or 0) >= 3
