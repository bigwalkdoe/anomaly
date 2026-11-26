from __future__ import annotations

from uuid import UUID

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    Evidence,
    EvidenceType,
    Report,
    Role,
    RoleName,
    Run,
    RunStatus,
    User,
)
from sqlalchemy import select


async def _seed_admin(db_session, email: str) -> User:
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is None:
        role = Role(name=RoleName.admin, description="admin")
        db_session.add(role)
        await db_session.flush()
    user = User(email=email, name="Admin", password_hash=hash_password("pass"), roles=[role])
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_engagement_with_evidence(db_session, owner: User):
    eng = Engagement(name="TraceEng", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=owner.id, role=RoleName.admin))
    run = Run(engagement_id=eng.id, user_id=owner.id, tool="nmap", status=RunStatus.succeeded)
    db_session.add(run)
    await db_session.flush()
    ev = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="logs/t.txt",
        sha256="b" * 64,
        collector="worker",
        tool="nmap",
        metadata={"sha256": "b" * 64},
    )
    db_session.add(ev)
    await db_session.commit()
    return eng, run, ev


@pytest.mark.asyncio
async def test_legacy_report_generate_includes_traceability(client, db_session):
    owner = await _seed_admin(db_session, "trace-legacy@example.com")
    eng, run, ev = await _seed_engagement_with_evidence(db_session, owner)
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, ['admin'])}"}

    resp = await client.get(
        f"/api/reports/engagements/{eng.id}/generate?format=markdown", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    trace = body["traceability"]
    assert trace["engagement_id"] == str(eng.id)
    assert str(run.id) in [trace.get("job_id"), trace.get("run_id"), trace.get("execution_id")]
    assert str(ev.id) in trace.get("evidence_ids", [])
    assert "b" * 64 in trace.get("evidence_sha256", [])
    assert trace.get("report_sha256")
    assert body["report_id"]

    list_resp = await client.get(f"/api/reports/engagements/{eng.id}", headers=headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert any(r["id"] == body["report_id"] for r in listed)

    from anomaly_core.models import AuditLog

    audit_rows = (
        await db_session.scalars(select(AuditLog).where(AuditLog.action == "report.list"))
    ).all()
    assert any(str(r.engagement_id) == str(eng.id) for r in audit_rows)


@pytest.mark.asyncio
async def test_v1_report_generate_includes_traceability(client, db_session):
    owner = await _seed_admin(db_session, "trace-v1@example.com")
    eng, run, ev = await _seed_engagement_with_evidence(db_session, owner)
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, ['admin'])}"}

    resp = await client.get(
        f"/api/v1/engagements/{eng.id}/reports/generate?format=markdown", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    trace = data["traceability"]
    assert trace["engagement_id"] == str(eng.id)
    assert str(ev.id) in trace.get("evidence_ids", [])
    assert "b" * 64 in trace.get("evidence_sha256", [])
    assert trace.get("report_sha256")

    list_resp = await client.get(f"/api/v1/engagements/{eng.id}/reports", headers=headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()["data"]
    assert any(r["id"] == data["report_id"] for r in listed)


@pytest.mark.asyncio
async def test_legacy_report_get_detects_tampered_content(client, db_session):
    """The break: reports had no recorded checksum to compare against stored content."""
    owner = await _seed_admin(db_session, "trace-tamper@example.com")
    eng, _run, _ev = await _seed_engagement_with_evidence(db_session, owner)
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, ['admin'])}"}
    gen = await client.get(
        f"/api/reports/engagements/{eng.id}/generate?format=markdown", headers=headers
    )
    assert gen.status_code == 200
    report_id = UUID(gen.json()["report_id"])
    original_sha = gen.json()["traceability"]["report_sha256"]

    report = await db_session.get(Report, report_id)
    assert report is not None
    report.content = "# TAMPERED"
    await db_session.commit()

    resp = await client.get(f"/api/reports/{report_id}", headers=headers)
    assert resp.status_code == 200
    trace = resp.json()["traceability"]
    assert trace["recorded_sha256"] == original_sha
    assert trace["report_sha256"] != original_sha
    assert trace["verified"] is False


@pytest.mark.asyncio
async def test_v1_report_get_detects_tampered_content(client, db_session):
    owner = await _seed_admin(db_session, "trace-v1-tamper@example.com")
    eng, _run, _ev = await _seed_engagement_with_evidence(db_session, owner)
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, ['admin'])}"}
    gen = await client.get(
        f"/api/v1/engagements/{eng.id}/reports/generate?format=markdown", headers=headers
    )
    assert gen.status_code == 200
    data = gen.json()["data"]
    report_id = UUID(data["report_id"])
    original_sha = data["traceability"]["report_sha256"]

    report = await db_session.get(Report, report_id)
    assert report is not None
    report.content = "# TAMPERED V1"
    await db_session.commit()

    resp = await client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert resp.status_code == 200
    trace = resp.json()["data"]["traceability"]
    assert trace["recorded_sha256"] == original_sha
    assert trace["report_sha256"] != original_sha
    assert trace["verified"] is False
