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
    Target,
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


@pytest.mark.asyncio
async def test_execute_run_marks_timeout_as_failed_and_audits(db_session, monkeypatch):
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )

    class _SlowRunner:
        specs = []

        async def run(self, spec):
            self.specs.append(spec)
            raise TimeoutError()

    async def _raise_timeout(awaitable, timeout=None):
        import contextlib

        with contextlib.suppress(Exception):
            awaitable.close()
        raise TimeoutError()

    monkeypatch.setattr("anomaly_worker.executor.asyncio.wait_for", _raise_timeout)
    runner = _SlowRunner()

    result = await execute_run(db_session, run.id, runner=runner)

    assert result.status == RunStatus.failed
    audit_rows = (
        await db_session.scalars(select(AuditLog).where(AuditLog.resource_id == run.id))
    ).all()
    timeout_audits = [a for a in audit_rows if a.action == "run.timeout"]
    assert timeout_audits, "expected run.timeout audit event"


@pytest.mark.asyncio
async def test_execute_run_uses_docker_runner_when_env_selected(db_session, monkeypatch):
    _org, _engagement, run = await _setup_run(
        db_session, targets=["example.com"], scope_entries=["example.com"]
    )
    seen = {}

    class _StubDockerRunner:
        specs = []

        async def run(self, spec):
            self.specs.append(spec)
            seen["used"] = True
            return RunResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setenv("ANOMALY_RUNNER", "docker")
    monkeypatch.setattr("anomaly_worker.executor.DockerRunner", _StubDockerRunner)

    result = await execute_run(db_session, run.id, runner=None)

    assert result.status == RunStatus.succeeded
    assert seen.get("used") is True


@pytest.mark.asyncio
async def test_out_of_scope_target_fails_before_runner_execution(db_session):
    """The break: a runner invoked with an out-of-scope target would perform unauthorized work."""
    _org, _engagement, run = await _setup_run(
        db_session, targets=["evil.com"], scope_entries=["example.com"]
    )
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="should not run"))

    result = await execute_run(db_session, run.id, runner=runner)

    assert result.status == RunStatus.failed
    assert runner.specs == []
    audit = await _denied_audit(db_session, run)
    assert audit.metadata["reason"] == "out_of_scope"
    assert "evil.com" in audit.metadata["out_of_scope"]
    evidence = await db_session.scalar(select(Evidence).where(Evidence.run_id == run.id))
    assert evidence is None


@pytest.mark.asyncio
async def test_discovered_targets_outside_scope_are_not_persisted(db_session, monkeypatch):
    """The break: tool output can register out-of-scope targets without a scope check."""
    _org, _engagement, run = await _setup_run(
        db_session,
        targets=["example.com"],
        scope_entries=["example.com"],
        tool="custom",
    )

    class Tool:
        name = "custom"
        supported_target_types = ["domain"]

        def build_cmd(self, spec):
            return ["custom"]

        def parse(self, stdout):
            return type(
                "Parsed",
                (),
                {
                    "findings": [],
                    "discovered_targets": [
                        {"value": "app.example.com", "type": "domain"},
                        {"value": "evil.com", "type": "domain"},
                    ],
                },
            )()

    class Registry:
        def get(self, name):
            return Tool() if name == "custom" else None

    import anomaly_worker.executor as executor_module

    monkeypatch.setattr(executor_module, "get_default_registry", lambda: Registry())
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="custom output", stderr=""))

    await execute_run(db_session, run.id, runner=runner)

    values = (
        await db_session.scalars(
            select(Target.value).where(Target.engagement_id == run.engagement_id)
        )
    ).all()
    assert "app.example.com" in values
    assert "evil.com" not in values

    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "scope.discovered_rejected",
            AuditLog.resource_id == run.id,
        )
    )
    assert audit is not None
    assert audit.metadata["out_of_scope"] == ["evil.com"]
