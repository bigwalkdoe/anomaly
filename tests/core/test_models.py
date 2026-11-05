import pytest
from sqlalchemy import select

from anomaly_core.models.audit import AuditLog
from anomaly_core.models.engagement import Engagement, EngagementMode, EngagementStatus, Target
from anomaly_core.models.finding import Finding, FindingSeverity, FindingStatus
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.models.user import User


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(email="alice@example.com", name="Alice", password_hash="hashed", is_active=True)
    db_session.add(user)
    await db_session.commit()
    result = await db_session.scalar(select(User).where(User.email == "alice@example.com"))
    assert result is not None
    assert result.password_hash == "hashed"
    assert result.id is not None


@pytest.mark.asyncio
async def test_engagement_defaults(db_session):
    owner = User(email="owner@example.com", name="Owner", password_hash="x")
    db_session.add(owner)
    await db_session.flush()
    engagement = Engagement(
        name="Test",
        mode=EngagementMode.OWN_INFRA,
        owner_id=owner.id,
    )
    db_session.add(engagement)
    await db_session.commit()
    await db_session.refresh(engagement)
    assert engagement.status == EngagementStatus.DRAFT
    assert engagement.mode == EngagementMode.OWN_INFRA


@pytest.mark.asyncio
async def test_finding_linked_to_engagement_and_target(db_session):
    owner = User(email="o2@example.com", name="O2", password_hash="x")
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.CLIENT, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    target = Target(engagement_id=eng.id, value="example.com", type="domain", status="active")
    db_session.add(target)
    await db_session.flush()
    finding = Finding(
        engagement_id=eng.id,
        target_id=target.id,
        title="Issue",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.NEW,
        reporter_id=owner.id,
        fingerprint="fp1",
    )
    db_session.add(finding)
    await db_session.commit()
    result = await db_session.scalar(select(Finding).where(Finding.id == finding.id))
    assert result is not None
    assert result.engagement_id == eng.id
    assert result.target_id == target.id


@pytest.mark.asyncio
async def test_audit_log_entry(db_session):
    log = AuditLog(action="test.action", resource_type="test", metadata={"k": "v"})
    db_session.add(log)
    await db_session.commit()
    result = await db_session.scalar(select(AuditLog).where(AuditLog.id == log.id))
    assert result is not None
    assert result.action == "test.action"
    assert result.metadata["k"] == "v"


@pytest.mark.asyncio
async def test_run_scope_warning_defaults_false(db_session):
    owner = User(email="o3@example.com", name="O3", password_hash="x")
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(name="E2", mode=EngagementMode.BUG_BOUNTY, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    run = Run(
        engagement_id=eng.id,
        user_id=owner.id,
        tool="stub",
        target_ids=[],
        params={},
        status=RunStatus.QUEUED,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    assert run.scope_warning is False
