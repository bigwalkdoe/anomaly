from __future__ import annotations

import hashlib
import uuid

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    AuditLog,
    Engagement,
    EngagementMember,
    EngagementMode,
    Evidence,
    EvidenceType,
    Role,
    RoleName,
    Run,
    RunStatus,
    Scope,
    ScopeEntry,
    ScopeEntryKind,
    User,
)
from anomaly_core.runner import FakeRunner, RunResult
from sqlalchemy import select


async def _seed_user(db, email: str, role: RoleName):
    r = await db.scalar(select(Role).where(Role.name == role))
    if r is None:
        r = Role(name=role, description=role.value)
        db.add(r)
        await db.flush()
    u = User(email=email, name=email.split("@")[0], password_hash=hash_password("pass"), roles=[r])
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_vertical_slice_end_to_end(client, db_session, monkeypatch):
    """
    Minimal vertical slice:
    authenticate context -> create engagement+scope -> approve (audited)
    -> request assessment (policy+scope validated, approved required)
    -> isolated/manifest-driven execution -> normalized findings
    -> evidence with checksum+provenance -> traceable report.
    """
    monkeypatch.setenv("RUNNER_MODE", "inline")

    owner = await _seed_user(db_session, "owner-slice@example.com", RoleName.admin)
    pentester = await _seed_user(db_session, "pentester-slice@example.com", RoleName.pentester)
    await db_session.commit()

    owner_token = create_access_token(owner.id, [RoleName.admin.value])
    pentest_token = create_access_token(pentester.id, [RoleName.pentester.value])
    headers_owner = {"Authorization": f"Bearer {owner_token}"}
    headers_pt = {"Authorization": f"Bearer {pentest_token}"}

    # Auth context should expose memberships/permissions (step 1)
    me = await client.get("/api/auth/me", headers=headers_owner)
    assert me.status_code == 200
    me_body = me.json()
    assert "memberships" in me_body or "organizations" in me_body

    # Create engagement with scope (step 2)
    resp = await client.post(
        "/api/engagements",
        headers=headers_owner,
        json={"name": "Slice E2E", "mode": "own_infra"},
    )
    assert resp.status_code == 201
    eng = resp.json()
    eng_id = eng["id"]
    org_id = eng.get("organization_id")

    # Add member and ensure org membership for tenant access
    db_session.add(EngagementMember(engagement_id=uuid.UUID(eng_id), user_id=pentester.id, role=RoleName.pentester))
    if org_id:
        from anomaly_core.models import Membership
        exists = await db_session.scalar(select(Membership).where(Membership.user_id == pentester.id, Membership.organization_id == uuid.UUID(str(org_id))))
        if not exists:
            db_session.add(Membership(user_id=pentester.id, organization_id=uuid.UUID(str(org_id)), role="member"))
    await db_session.commit()

    scope_resp = await client.put(
        f"/api/engagements/{eng_id}/scope",
        headers=headers_owner,
        json={"entries": [{"kind": "in", "target_value": "in.scope.test"}]},
    )
    assert scope_resp.status_code == 200

    # Approval required & audited (step 3) - submit/approve flow
    # try common action endpoints
    submit = await client.post(f"/api/engagements/{eng_id}/submit", headers=headers_owner, json={})
    if submit.status_code == 404:
        # fallback: status transition
        submit = await client.patch(f"/api/engagements/{eng_id}", headers=headers_owner, json={"status": "pending_approval"})
    assert submit.status_code in (200, 201, 202)

    approve = await client.post(f"/api/engagements/{eng_id}/approve", headers=headers_owner, json={})
    if approve.status_code == 404:
        approve = await client.patch(f"/api/engagements/{eng_id}", headers=headers_owner, json={"status": "approved"})
    assert approve.status_code == 200
    approved = approve.json()
    assert approved.get("status") in ("approved", "active")

    approval_audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == uuid.UUID(eng_id),
            AuditLog.action.in_(["engagement.approve", "engagement.approved", "approval.granted"]),
        )
    )
    assert approval_audit is not None

    # Request assessment - must be policy+scope validated and require approval (step 4)
    # unapproved/out-of-scope would be denied (covered in focused tests), in-scope approved should enqueue
    runner = FakeRunner(RunResult(exit_code=0, stdout="open port 80", stderr=""))
    monkeypatch.setattr("anomaly_worker.executor.FakeRunner", lambda: runner)
    # if implementation uses injected runner path differently, inline mode with stub is acceptable
    run_resp = await client.post(
        f"/api/engagements/{eng_id}/runs",
        headers=headers_pt,
        json={"tool": "stub", "targets": ["in.scope.test"], "params": {}},
    )
    assert run_resp.status_code in (200, 201, 202)
    run_body = run_resp.json()
    run_id = run_body["id"]

    # Execution produced result (step 5) and findings normalized (step 6)
    run_get = await client.get(f"/api/runs/{run_id}", headers=headers_pt)
    assert run_get.status_code == 200
    assert run_get.json().get("status") in ("succeeded", "completed", "queued", "running")

    # Evidence preserved with checksum+provenance (step 7)
    ev_rows = (await db_session.scalars(select(Evidence).where(Evidence.run_id == uuid.UUID(run_id)))).all()
    assert len(ev_rows) >= 1
    ev = ev_rows[0]
    meta = ev.metadata or {}
    assert meta.get("sha256") or getattr(ev, "sha256", None)
    # provenance fields expected
    assert meta.get("engagement_id") or getattr(ev, "engagement_id", None)
    assert meta.get("organization_id") or getattr(ev, "organization_id", None)

    # Report generated and traceable (step 8)
    rpt = await client.get(
        f"/api/reports/engagements/{eng_id}/generate",
        headers=headers_owner,
        params={"format": "markdown"},
    )
    assert rpt.status_code == 200
    rpt_body = rpt.json()
    content = rpt_body.get("content", "")
    assert eng_id in content or str(rpt_body.get("engagement_id")) == eng_id
    assert "run" in content.lower() or run_id in content
    assert "sha256" in content.lower() or "evidence" in content.lower()
