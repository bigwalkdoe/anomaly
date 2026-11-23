from __future__ import annotations

import hashlib
import uuid

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models import (
    AuditLog,
    Engagement,
    EngagementMode,
    EngagementStatus,
    Evidence,
    Organization,
    Run,
    RunStatus,
    Scope,
    ScopeEntry,
    User,
)
from anomaly_core.runner import FakeRunner, RunResult
from anomaly_worker.executor import (
    DEFAULT_RESOURCE_LIMITS,
    DEFAULT_RUN_TIMEOUT_S,
    MAX_EVIDENCE_TEXT_BYTES,
    MAX_TARGETS_PER_RUN,
    execute_run,
)
from sqlalchemy import select


async def _setup_run(
    db_session,
    *,
    targets: list[str],
    scope_entries: list[str],
    tool: str = "stub",
) -> tuple[Organization, Engagement, Run]:
    """Create an approved engagement with scope plus a queued run for executor tests."""
    org = Organization(name="Guardrail Org", slug=f"guardrail-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"guardrail-{uuid.uuid4().hex[:8]}@example.com",
        name="Guardrail Tester",
        password_hash=hash_password("pw"),
    )
    db_session.add(user)
    await db_session.flush()

    engagement = Engagement(
        organization_id=org.id,
        name="Guardrail Engagement",
        mode=EngagementMode.own_infra,
        owner_id=user.id,
        status=EngagementStatus.approved,
    )
    db_session.add(engagement)
    await db_session.flush()

    scope = Scope(engagement_id=engagement.id)
    db_session.add(scope)
    await db_session.flush()
    for entry in scope_entries:
        db_session.add(ScopeEntry(scope_id=scope.id, kind="in", target_value=entry))

    run = Run(
        organization_id=org.id,
        engagement_id=engagement.id,
        user_id=user.id,
        tool=tool,
        target_ids=[],
        params={"targets": targets},
        status=RunStatus.queued,
    )
    db_session.add(run)
    await db_session.commit()
    return org, engagement, run


async def _denied_audit(db_session, run: Run) -> AuditLog:
    entry = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "policy.denied",
            AuditLog.resource_id == run.id,
        )
    )
    assert entry is not None, "expected a policy.denied audit entry"
    return entry


@pytest.mark.asyncio
async def test_too_many_targets_fails_run_and_audits_without_executing(db_session):
    targets = [f"t{i}.example.com" for i in range(MAX_TARGETS_PER_RUN + 1)]
    org, _engagement, run = await _setup_run(
        db_session, targets=targets, scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="should not run"))

    result = await execute_run(db_session, run.id, runner=runner)

    assert result.status == RunStatus.failed
    assert runner.specs == [], "runner must not be invoked when target limit is exceeded"

    audit = await _denied_audit(db_session, run)
    meta = audit.metadata
    assert meta["reason"] == "too_many_targets"
    assert meta["target_count"] == MAX_TARGETS_PER_RUN + 1
    assert meta["max_targets"] == MAX_TARGETS_PER_RUN
    assert meta["op"] == "assessment.execute"
    assert audit.engagement_id == run.engagement_id
    assert audit.organization_id == org.id

    evidence_row = await db_session.scalar(select(Evidence).where(Evidence.run_id == run.id))
    assert evidence_row is None, "failed guardrail run must not store evidence"


@pytest.mark.asyncio
async def test_targets_at_limit_still_execute(db_session):
    assert MAX_TARGETS_PER_RUN == 256
    targets = [f"10.0.0.{i}" for i in range(1, 201)] + [f"10.0.1.{i}" for i in range(1, 57)]
    assert len(targets) == MAX_TARGETS_PER_RUN
    _org, _engagement, run = await _setup_run(
        db_session, targets=targets, scope_entries=["10.0.0.0/8"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="ok"))

    result = await execute_run(db_session, run.id, runner=runner)

    assert result.status == RunStatus.succeeded
    assert len(runner.specs) == 1
    assert len(runner.specs[0].target_values) == MAX_TARGETS_PER_RUN
    denied = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "policy.denied",
            AuditLog.resource_id == run.id,
        )
    )
    assert denied is None


@pytest.mark.asyncio
async def test_evidence_truncates_stored_output_and_flags_metadata(db_session):
    stdout = "A" * (MAX_EVIDENCE_TEXT_BYTES + 100)
    stderr = "B" * 50
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout=stdout, stderr=stderr))

    await execute_run(db_session, run.id, runner=runner)

    evidence = await db_session.scalar(select(Evidence).where(Evidence.run_id == run.id))
    assert evidence is not None
    meta = evidence.metadata

    assert meta["stdout_truncated"] is True
    assert meta["stderr_truncated"] is False
    assert meta["stdout"] == "A" * MAX_EVIDENCE_TEXT_BYTES
    assert len(meta["stdout"].encode("utf-8")) == MAX_EVIDENCE_TEXT_BYTES
    assert meta["stderr"] == stderr

    full_sha = hashlib.sha256((stdout + "\n" + stderr).encode("utf-8")).hexdigest()
    truncated_sha = hashlib.sha256(
        ("A" * MAX_EVIDENCE_TEXT_BYTES + "\n" + stderr).encode("utf-8")
    ).hexdigest()
    assert full_sha != truncated_sha, "sanity: truncated payload hash must differ"
    assert evidence.sha256 == full_sha
    assert meta["sha256"] == full_sha


@pytest.mark.asyncio
async def test_evidence_truncates_large_stderr_and_preserves_full_hash(db_session):
    stdout = "A" * 50
    stderr = "B" * (MAX_EVIDENCE_TEXT_BYTES + 100)
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout=stdout, stderr=stderr))

    await execute_run(db_session, run.id, runner=runner)

    evidence = await db_session.scalar(select(Evidence).where(Evidence.run_id == run.id))
    assert evidence is not None
    meta = evidence.metadata

    assert meta["stdout_truncated"] is False
    assert meta["stderr_truncated"] is True
    assert meta["stdout"] == stdout
    assert meta["stderr"] == "B" * MAX_EVIDENCE_TEXT_BYTES
    assert len(meta["stderr"].encode("utf-8")) == MAX_EVIDENCE_TEXT_BYTES

    full_sha = hashlib.sha256((stdout + "\n" + stderr).encode("utf-8")).hexdigest()
    assert evidence.sha256 == full_sha
    assert meta["sha256"] == full_sha


@pytest.mark.asyncio
async def test_evidence_preserves_small_output_without_truncation_flags(db_session):
    stdout = "small stdout"
    stderr = "small stderr"
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout=stdout, stderr=stderr))

    await execute_run(db_session, run.id, runner=runner)

    evidence = await db_session.scalar(select(Evidence).where(Evidence.run_id == run.id))
    assert evidence is not None
    meta = evidence.metadata

    assert meta["stdout_truncated"] is False
    assert meta["stderr_truncated"] is False
    assert meta["stdout"] == stdout
    assert meta["stderr"] == stderr
    full_sha = hashlib.sha256((stdout + "\n" + stderr).encode("utf-8")).hexdigest()
    assert evidence.sha256 == full_sha


@pytest.mark.asyncio
async def test_run_spec_uses_default_timeout_and_resource_limits(db_session):
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="ok"))

    await execute_run(db_session, run.id, runner=runner)

    assert len(runner.specs) == 1
    spec = runner.specs[0]
    assert spec.timeout_s == DEFAULT_RUN_TIMEOUT_S == 300
    assert spec.resource_limits == DEFAULT_RESOURCE_LIMITS
    assert spec.resource_limits == {"mem_limit": "512m", "pids_limit": 256}
