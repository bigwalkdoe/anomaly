
import uuid

import pytest
import pytest_asyncio
from anomaly_core.db import Base, SessionLocal, engine
from anomaly_core.models import (
    Approval,
    AuditLog,
    Engagement,
    EngagementMode,
    EngagementStatus,
    Evidence,
    EvidenceType,
    Finding,
    FindingSeverity,
    FindingStatus,
    Run,
    RunStatus,
    Target,
    TargetType,
    User,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(loop_scope="session")
async def session():
    async with SessionLocal() as db:
        yield db
        await db.rollback()


@pytest.mark.asyncio
async def test_create_user(session):
    user = User(email="user@example.com", name="Test User", password_hash="hashed-secret")
    session.add(user)
    await session.flush()
    assert user.id is not None
    assert user.password_hash == "hashed-secret"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_engagement_defaults(session):
    import uuid
    user = User(email=f"owner-{uuid.uuid4()}@example.com", name="Owner", password_hash="x")
    session.add(user)
    await session.flush()
    engagement = Engagement(name="Test Engagement", owner_id=user.id)
    session.add(engagement)
    await session.flush()
    assert engagement.mode == EngagementMode.own_infra
    assert engagement.status == EngagementStatus.draft
    assert engagement.client_name is None


@pytest.mark.asyncio
async def test_finding_linked(session):
    user = User(email="reporter@example.com", name="Reporter", password_hash="x")
    session.add(user)
    await session.flush()
    engagement = Engagement(name="Eng", owner_id=user.id)
    session.add(engagement)
    await session.flush()
    target = Target(engagement_id=engagement.id, value="example.com", type=TargetType.domain)
    session.add(target)
    await session.flush()
    finding = Finding(
        engagement_id=engagement.id,
        target_id=target.id,
        title="Test Finding",
        reporter_id=user.id,
        fingerprint="fp-1",
    )
    session.add(finding)
    await session.flush()
    assert finding.id is not None
    assert finding.target_id == target.id
    assert finding.engagement_id == engagement.id
    assert finding.severity == FindingSeverity.medium
    assert finding.status == FindingStatus.new
    assert finding.ai_drafted is False


@pytest.mark.asyncio
async def test_audit_log(session):
    entry = AuditLog(action="create", resource_type="engagement", metadata={"key": "value"})
    session.add(entry)
    await session.flush()
    assert entry.id is not None
    assert entry.created_at is not None
    assert entry.metadata == {"key": "value"}
    assert entry.actor_id is None


@pytest.mark.asyncio
async def test_run_scope_warning_default(session):
    user = User(email="runner@example.com", name="Runner", password_hash="x")
    session.add(user)
    await session.flush()
    engagement = Engagement(name="Eng2", owner_id=user.id)
    session.add(engagement)
    await session.flush()
    run = Run(engagement_id=engagement.id, user_id=user.id, tool="nmap", target_ids=[])
    session.add(run)
    await session.flush()
    assert run.scope_warning is False
    assert run.status == RunStatus.queued
    assert run.params == {}


@pytest.mark.asyncio
async def test_run_target_ids_uuid(session):
    user = User(email="runner2@example.com", name="Runner2", password_hash="x")
    session.add(user)
    await session.flush()
    engagement = Engagement(name="Eng3", owner_id=user.id)
    session.add(engagement)
    await session.flush()
    uid = uuid.uuid4()
    run = Run(engagement_id=engagement.id, user_id=user.id, tool="nmap", target_ids=[uid])
    session.add(run)
    await session.flush()
    assert run.id is not None
    assert len(run.target_ids) == 1
    assert str(run.target_ids[0]) == str(uid)


@pytest.mark.asyncio
async def test_approval_resource_id_uuid(session):
    user = User(email="approver@example.com", name="Approver", password_hash="x")
    session.add(user)
    await session.flush()
    rid = uuid.uuid4()
    approval = Approval(
        resource_type="finding",
        resource_id=rid,
        requester_id=user.id,
    )
    session.add(approval)
    await session.flush()
    assert approval.id is not None
    assert approval.resource_id is not None
    assert str(approval.resource_id) == str(rid)


@pytest.mark.asyncio
async def test_updated_at_present(session):
    user = User(email="u3@example.com", name="U3", password_hash="x")
    session.add(user)
    await session.flush()
    engagement = Engagement(name="Eng4", owner_id=user.id)
    session.add(engagement)
    await session.flush()
    target = Target(engagement_id=engagement.id, value="example.com", type=TargetType.domain)
    session.add(target)
    await session.flush()
    assert target.updated_at is not None
    evidence = Evidence(type=EvidenceType.log, storage_key="key")
    session.add(evidence)
    await session.flush()
    assert evidence.updated_at is not None
    run = Run(engagement_id=engagement.id, user_id=user.id, tool="nmap", target_ids=[])
    session.add(run)
    await session.flush()
    assert run.updated_at is not None