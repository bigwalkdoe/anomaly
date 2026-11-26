from __future__ import annotations

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.findings import finding_fingerprint
from anomaly_core.models import (
    Engagement,
    EngagementMode,
    EngagementStatus,
    Finding,
    FindingStatus,
    Organization,
    Run,
    RunStatus,
    Scope,
    ScopeEntry,
    User,
)
from anomaly_core.runner import FakeRunner, RunResult
from anomaly_worker.executor import execute_run
from sqlalchemy import select


async def _setup_run(db_session, *, tool: str = "stub"):
    """Create an approved engagement with one target and a queued run."""
    import uuid

    org = Organization(name="Fingerprint Org", slug=f"fp-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        email=f"fp-{uuid.uuid4().hex[:8]}@example.com",
        name="Fingerprint Tester",
        password_hash=hash_password("pw"),
    )
    db_session.add(user)
    await db_session.flush()

    engagement = Engagement(
        organization_id=org.id,
        name="Fingerprint Engagement",
        mode=EngagementMode.own_infra,
        owner_id=user.id,
        status=EngagementStatus.approved,
    )
    db_session.add(engagement)
    await db_session.flush()

    scope = Scope(engagement_id=engagement.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(ScopeEntry(scope_id=scope.id, kind="in", target_value="example.com"))

    run = Run(
        organization_id=org.id,
        engagement_id=engagement.id,
        user_id=user.id,
        tool=tool,
        target_ids=[],
        params={"targets": ["example.com"]},
        status=RunStatus.queued,
    )
    db_session.add(run)
    await db_session.commit()
    return engagement, run, user


@pytest.mark.asyncio
async def test_executor_fingerprints_are_stable_across_runs(db_session):
    """The break: run.id in the fingerprint duplicates identical findings across runs."""
    engagement, run1, _user1 = await _setup_run(db_session)
    _engagement, run2, _user2 = await _setup_run(db_session)
    # Same engagement and target content, different run identities.
    run2.engagement_id = engagement.id
    await db_session.commit()
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="", stderr=""))

    await execute_run(db_session, run1.id, runner=runner)
    await execute_run(db_session, run2.id, runner=runner)

    fps = (
        await db_session.scalars(
            select(Finding.fingerprint).where(Finding.engagement_id == engagement.id)
        )
    ).all()
    assert len(fps) == 1, "identical findings across runs must deduplicate"


@pytest.mark.asyncio
async def test_executor_preserves_parser_supplied_fingerprint(db_session, monkeypatch):
    """Tool-provided fingerprints remain authoritative for normalization."""
    _engagement, run, _user = await _setup_run(db_session, tool="custom")
    run.tool = "custom"
    await db_session.commit()

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
                    "findings": [
                        {
                            "fingerprint": "tool-fp-001",
                            "title": "Custom",
                            "description": "x",
                        }
                    ],
                    "discovered_targets": [],
                },
            )()

    class Registry:
        def get(self, name):
            return Tool() if name == "custom" else None

    import anomaly_worker.executor as executor_module

    monkeypatch.setattr(executor_module, "get_default_registry", lambda: Registry())
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="custom output", stderr=""))

    await execute_run(db_session, run.id, runner=runner)

    fps = (await db_session.scalars(select(Finding.fingerprint))).all()
    assert fps == ["tool-fp-001"]


@pytest.mark.asyncio
async def test_manual_and_executor_findings_share_fingerprint(db_session):
    """The break: manual and tool-produced findings use incompatible fingerprint schemes."""
    engagement, run, user = await _setup_run(db_session)
    db_session.add(
        Finding(
            engagement_id=engagement.id,
            title="Stub finding: target reachable",
            severity="info",
            description="Stub finding for example.com",
            status=FindingStatus.new,
            reporter_id=user.id,
            fingerprint=finding_fingerprint(
                engagement.id,
                "Stub finding: target reachable",
                "Stub finding for example.com",
            ),
        )
    )
    await db_session.commit()
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="", stderr=""))

    await execute_run(db_session, run.id, runner=runner)

    fps = (
        await db_session.scalars(
            select(Finding.fingerprint).where(Finding.engagement_id == engagement.id)
        )
    ).all()
    assert len(fps) == 1, "identical findings across runs must deduplicate"
