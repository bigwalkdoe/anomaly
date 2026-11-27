from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models import (
    AuditLog,
    CronSchedule,
    Engagement,
    EngagementMode,
    EngagementStatus,
    Role,
    RoleName,
    Run,
    RunStatus,
    Scope,
    ScopeEntry,
    ScopeEntryKind,
    User,
)
from anomaly_core.scheduler import compute_next_run_at, dispatch_due_schedules
from sqlalchemy import select


async def _seed_admin(db_session, email: str) -> User:
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is None:
        role = Role(name=RoleName.admin, description="admin")
        db_session.add(role)
        await db_session.flush()
    user = User(
        email=email,
        name=email.split("@")[0],
        password_hash=hash_password("pass"),
        roles=[role],
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_engagement(db_session, owner: User, *, approved: bool = True) -> Engagement:
    eng = Engagement(
        name="Sched Eng",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved if approved else EngagementStatus.draft,
    )
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    )
    await db_session.flush()
    return eng


@pytest.mark.asyncio
async def test_dispatch_due_schedule_enqueues_run_and_advances(db_session):
    owner = await _seed_admin(db_session, "sched-owner@example.com")
    eng = await _seed_engagement(db_session, owner, approved=True)
    now = datetime.now(UTC)
    sched = CronSchedule(
        engagement_id=eng.id,
        cron_expression="*/5 * * * *",
        tool="nmap",
        targets=["example.com"],
        params={"ports": "80"},
        is_active=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    results = await dispatch_due_schedules(db_session, now=now)
    assert len(results) == 1
    assert results[0].status == "dispatched"
    assert results[0].run_id is not None

    run = await db_session.get(Run, results[0].run_id)
    assert run is not None
    assert run.status == RunStatus.queued
    assert run.tool == "nmap"
    assert run.engagement_id == eng.id
    assert run.user_id == owner.id
    assert run.params["targets"] == ["example.com"]
    assert run.params["ports"] == "80"
    assert isinstance(run.params.get("execution_manifest"), dict)
    assert run.params["execution_manifest"]["run_id"] == str(run.id)
    execution_policy = run.params["execution_manifest"]["execution_policy"]
    assert execution_policy["allowed"] is True
    assert execution_policy["reason"] is None
    assert execution_policy["targets"] == ["example.com"]

    await db_session.refresh(sched)
    assert sched.next_run_at is not None
    assert sched.next_run_at > now
    assert sched.last_dispatch_status == "dispatched"
    assert sched.last_error is None
    assert sched.last_dispatch_at is not None
    assert int(sched.dispatch_count or 0) == 1

    audit_actions = (
        await db_session.scalars(select(AuditLog.action).where(AuditLog.engagement_id == eng.id))
    ).all()
    assert "run.enqueue" in audit_actions
    assert "schedule.dispatch" in audit_actions


@pytest.mark.asyncio
async def test_dispatch_policy_denied_skips_and_advances(db_session):
    owner = await _seed_admin(db_session, "sched-deny@example.com")
    eng = await _seed_engagement(db_session, owner, approved=False)  # not approved
    now = datetime.now(UTC)
    sched = CronSchedule(
        engagement_id=eng.id,
        cron_expression="*/5 * * * *",
        tool="nmap",
        targets=["example.com"],
        params={},
        is_active=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    results = await dispatch_due_schedules(db_session, now=now)
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert results[0].reason == "policy_denied"
    assert results[0].run_id is None

    runs = (await db_session.scalars(select(Run).where(Run.engagement_id == eng.id))).all()
    assert runs == []

    await db_session.refresh(sched)
    assert sched.is_active is True
    assert sched.next_run_at is not None and sched.next_run_at > now
    assert sched.last_dispatch_status == "denied"
    assert sched.last_error
    assert sched.last_dispatch_at is not None
    assert int(sched.dispatch_count or 0) == 1

    actions = (
        await db_session.scalars(select(AuditLog.action).where(AuditLog.engagement_id == eng.id))
    ).all()
    assert "policy.denied" in actions
    assert "schedule.dispatch_denied" in actions


@pytest.mark.asyncio
async def test_dispatch_out_of_scope_denial_records_scope_context(db_session):
    owner = await _seed_admin(db_session, "sched-scope@example.com")
    eng = await _seed_engagement(db_session, owner, approved=True)
    now = datetime.now(UTC)
    sched = CronSchedule(
        engagement_id=eng.id,
        cron_expression="*/5 * * * *",
        tool="nmap",
        targets=["evil.example.net"],
        params={},
        is_active=True,
        next_run_at=now - timedelta(minutes=1),
    )
    db_session.add(sched)
    await db_session.commit()

    results = await dispatch_due_schedules(db_session, now=now)

    assert results[0].status == "skipped"
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id, AuditLog.action == "policy.denied"
        )
    )
    assert audit is not None
    assert audit.metadata["allowed"] is False
    assert audit.metadata["reason"] == "out_of_scope"
    assert audit.metadata["out_of_scope"] == ["evil.example.net"]
    assert audit.metadata["has_warning"] is True


@pytest.mark.asyncio
async def test_dispatch_initializes_null_next_run_and_not_due_is_ignored(db_session):
    owner = await _seed_admin(db_session, "sched-init@example.com")
    eng = await _seed_engagement(db_session, owner, approved=True)
    now = datetime.now(UTC)
    sched_null = CronSchedule(
        engagement_id=eng.id,
        cron_expression="0 0 1 1 *",  # far future relative to most now
        tool="nmap",
        targets=["example.com"],
        params={},
        is_active=True,
        next_run_at=None,
    )
    sched_future = CronSchedule(
        engagement_id=eng.id,
        cron_expression="*/5 * * * *",
        tool="nmap",
        targets=["example.com"],
        params={},
        is_active=True,
        next_run_at=now + timedelta(hours=1),
    )
    db_session.add_all([sched_null, sched_future])
    await db_session.commit()

    results = await dispatch_due_schedules(db_session, now=now)
    by_id = {r.schedule_id: r for r in results}
    assert by_id[sched_null.id].status == "skipped"
    assert by_id[sched_null.id].reason == "next_run_initialized"
    assert sched_future.id not in by_id  # not due, ignored

    await db_session.refresh(sched_null)
    assert sched_null.next_run_at is not None
    assert sched_null.next_run_at > now
    assert sched_null.last_dispatch_status == "initialized"
    assert sched_null.last_dispatch_at is not None

    runs = (await db_session.scalars(select(Run))).all()
    assert runs == []


def test_compute_next_run_at_returns_future_datetime():
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    nxt = compute_next_run_at("*/10 * * * *", base=base)
    assert nxt > base
    assert nxt.minute in (10, 20, 30, 40, 50, 0)