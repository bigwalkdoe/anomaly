from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from anomaly_core.models import (
    Engagement,
    EngagementMode,
    Evidence,
    EvidenceType,
    Report,
    ReportFormat,
    ReportStatus,
    Role,
    RoleName,
    Run,
    RunStatus,
    User,
)
from anomaly_core.retention import purge_expired_records
from sqlalchemy import select


async def _get_admin_role(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is None:
        role = Role(name=RoleName.admin, description="admin")
        db_session.add(role)
        await db_session.flush()
    return role


def _settings(monkeypatch, **overrides):
    from anomaly_core import config

    base = dict(
        database_url="sqlite+aiosqlite://",
        redis_url="redis://localhost",
        jwt_secret="s",
        minio_endpoint="localhost:9000",
        minio_access_key="a",
        minio_secret_key="b",
    )
    base.update(overrides)
    monkeypatch.setattr(config, "_settings", config.Settings(**base))


@pytest.mark.asyncio
async def test_purge_expired_records_disabled_by_default(db_session, monkeypatch):
    _settings(monkeypatch)
    role = await _get_admin_role(db_session)
    user = User(email="r@example.com", name="R", password_hash="x", roles=[role])
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    run = Run(engagement_id=eng.id, user_id=user.id, tool="nmap", status=RunStatus.succeeded)
    db_session.add(run)
    await db_session.flush()
    old = datetime.now(UTC) - timedelta(days=999)
    ev = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="k",
        sha256="a" * 64,
        metadata={},
    )
    ev.created_at = old
    rep = Report(
        engagement_id=eng.id,
        version=1,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="x",
        author_id=user.id,
    )
    rep.created_at = old
    db_session.add_all([ev, rep])
    await db_session.commit()

    deleted = await purge_expired_records(db_session)
    assert deleted == {"evidence": 0, "reports": 0}
    assert await db_session.scalar(select(Evidence.id).where(Evidence.id == ev.id)) is not None


@pytest.mark.asyncio
async def test_purge_expired_records_deletes_old_rows(db_session, monkeypatch):
    now = datetime.now(UTC)
    _settings(monkeypatch, evidence_retention_days=30, report_retention_days=30)
    role = await _get_admin_role(db_session)
    user = User(email="r2@example.com", name="R2", password_hash="x", roles=[role])
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    run = Run(engagement_id=eng.id, user_id=user.id, tool="nmap", status=RunStatus.succeeded)
    db_session.add(run)
    await db_session.flush()
    old = now - timedelta(days=45)
    fresh = now - timedelta(days=5)
    ev_old = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="k1",
        sha256="a" * 64,
        metadata={},
    )
    ev_old.created_at = old
    ev_new = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="k2",
        sha256="b" * 64,
        metadata={},
    )
    ev_new.created_at = fresh
    rep_old = Report(
        engagement_id=eng.id,
        version=1,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="old",
        author_id=user.id,
    )
    rep_old.created_at = old
    rep_new = Report(
        engagement_id=eng.id,
        version=2,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="new",
        author_id=user.id,
    )
    rep_new.created_at = fresh
    db_session.add_all([ev_old, ev_new, rep_old, rep_new])
    await db_session.commit()

    deleted = await purge_expired_records(db_session, now=now)
    assert deleted == {"evidence": 1, "reports": 1}
    assert await db_session.scalar(select(Evidence.id).where(Evidence.id == ev_old.id)) is None
    assert await db_session.scalar(select(Evidence.id).where(Evidence.id == ev_new.id)) is not None
    assert await db_session.scalar(select(Report.id).where(Report.id == rep_old.id)) is None
    assert await db_session.scalar(select(Report.id).where(Report.id == rep_new.id)) is not None
