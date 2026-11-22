from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    Finding,
    FindingSeverity,
    Role,
    RoleName,
    User,
)
from fastapi import HTTPException
from sqlalchemy import select


async def _get_role(db_session, name: RoleName) -> Role:
    """Fetch a role seeded by ensure_default_rbac (conftest); fail loudly if missing."""
    role = await db_session.scalar(select(Role).where(Role.name == name))
    assert role is not None, f"role {name} should be seeded by ensure_default_rbac"
    return role


async def _make_user(
    db_session,
    role: Role,
    email: str,
    name: str,
    memberships: list[tuple[Engagement, RoleName]] | None = None,
) -> User:
    user = User(email=email, name=name, password_hash=hash_password("pass"), roles=[role])
    db_session.add(user)
    await db_session.flush()
    for engagement, membership_role in memberships or []:
        db_session.add(
            EngagementMember(engagement_id=engagement.id, user_id=user.id, role=membership_role)
        )
    await db_session.flush()
    return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, ['pentester'])}"}


@pytest.mark.asyncio
async def test_admin_can_access_any_engagement(client, db_session):
    admin = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "admin@example.com", "Admin"
    )
    eng = Engagement(name="Test", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.commit()

    resp = await client.get(f"/api/engagements/{eng.id}", headers=_auth(admin))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pentester_can_access_assigned_engagements_only(client, db_session):
    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    pentester = await _make_user(
        db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P"
    )
    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng1.id, user_id=pentester.id, role=RoleName.pentester)
    )
    await db_session.commit()

    resp1 = await client.get(f"/api/engagements/{eng1.id}", headers=_auth(pentester))
    assert resp1.status_code == 200
    resp2 = await client.get(f"/api/engagements/{eng2.id}", headers=_auth(pentester))
    # Non-member access must not leak engagement existence.
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_client_viewer_no_runs_and_no_create(client, db_session):
    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "v@example.com",
        "V",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    await db_session.commit()

    headers = _auth(viewer)
    # read findings/reports is allowed
    resp_findings = await client.get(f"/api/engagements/{eng.id}/findings", headers=headers)
    assert resp_findings.status_code == 200
    resp_reports = await client.get(f"/api/reports/engagements/{eng.id}", headers=headers)
    assert resp_reports.status_code == 200
    # runs are never readable for client_viewer
    resp_runs = await client.get(f"/api/engagements/{eng.id}/runs", headers=headers)
    assert resp_runs.status_code == 403
    # creating findings is forbidden
    resp_create = await client.post(
        f"/api/engagements/{eng.id}/findings",
        headers=headers,
        json={"title": "x", "severity": "high", "description": "d"},
    )
    assert resp_create.status_code == 403
    # creating runs is forbidden
    resp_run = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "nmap", "targets": []},
    )
    assert resp_run.status_code == 403
    # report generation persists artifacts and is forbidden for client_viewer
    resp_report_gen = await client.get(
        f"/api/reports/engagements/{eng.id}/generate", headers=headers
    )
    assert resp_report_gen.status_code == 403
    resp_report_gen_v1 = await client.post(
        f"/api/v1/engagements/{eng.id}/reports", headers=headers, json={"format": "markdown"}
    )
    assert resp_report_gen_v1.status_code == 403
    resp_report_gen_v1_get = await client.get(
        f"/api/v1/engagements/{eng.id}/reports/generate", headers=headers
    )
    assert resp_report_gen_v1_get.status_code == 403


@pytest.mark.asyncio
async def test_unassigned_user_gets_403_on_engagement_endpoints(client, db_session):
    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    other = await _make_user(
        db_session, await _get_role(db_session, RoleName.pentester), "o@example.com", "O"
    )
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    resp = await client.get(f"/api/engagements/{eng.id}", headers=_auth(other))
    assert resp.status_code == 404
    resp_runs = await client.get(f"/api/engagements/{eng.id}/runs", headers=_auth(other))
    assert resp_runs.status_code == 404
    resp_findings = await client.get(f"/api/engagements/{eng.id}/findings", headers=_auth(other))
    assert resp_findings.status_code == 404


@pytest.mark.asyncio
async def test_cross_engagement_finding_read_returns_404(client, db_session):
    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    p = await _make_user(
        db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P"
    )
    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=p.id, role=RoleName.pentester))
    finding = Finding(
        engagement_id=eng2.id,
        title="x",
        severity=FindingSeverity.high,
        description="d",
        reporter_id=owner.id,
        fingerprint="fp1",
    )
    db_session.add(finding)
    await db_session.commit()

    resp = await client.get(f"/api/findings/{finding.id}", headers=_auth(p))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_client_viewer_cross_engagement_finding_returns_404(client, db_session):
    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    viewer = await _make_user(
        db_session, await _get_role(db_session, RoleName.client_viewer), "v2@example.com", "V2"
    )
    eng1 = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng1.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    finding = Finding(
        engagement_id=eng2.id,
        title="x",
        severity=FindingSeverity.high,
        description="d",
        reporter_id=owner.id,
        fingerprint="fp2",
    )
    db_session.add(finding)
    await db_session.commit()

    resp = await client.get(f"/api/findings/{finding.id}", headers=_auth(viewer))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_access_across_engagements_returns_404(client, db_session):
    from anomaly_core.models import Run, RunStatus

    owner = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner"
    )
    p = await _make_user(
        db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P"
    )
    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=p.id, role=RoleName.pentester))
    run = Run(
        engagement_id=eng2.id,
        user_id=owner.id,
        tool="nmap",
        status=RunStatus.queued,
    )
    db_session.add(run)
    await db_session.commit()

    resp = await client.get(f"/api/runs/{run.id}", headers=_auth(p))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_client_viewer_cannot_read_run_detail_or_status(client, db_session):
    from anomaly_core.models import Run, RunStatus

    owner = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.admin),
        "owner-run-view@example.com",
        "Owner",
    )
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "viewer-run-view@example.com",
        "Viewer",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    run = Run(
        engagement_id=eng.id,
        user_id=owner.id,
        tool="nmap",
        status=RunStatus.queued,
    )
    db_session.add(run)
    await db_session.commit()

    headers = _auth(viewer)
    resp = await client.get(f"/api/runs/{run.id}", headers=headers)
    assert resp.status_code == 403
    resp_v1 = await client.get(f"/api/v1/runs/{run.id}", headers=headers)
    assert resp_v1.status_code == 403
    resp_ws_status = await client.get(f"/api/ws/runs/{run.id}/status", headers=headers)
    assert resp_ws_status.status_code == 403


@pytest.mark.asyncio
async def test_seeded_roles_have_default_permissions(db_session):
    admin = await _get_role(db_session, RoleName.admin)
    pentester = await _get_role(db_session, RoleName.pentester)
    viewer = await _get_role(db_session, RoleName.client_viewer)
    assert {p.name for p in admin.permissions} == {"*"}
    assert {p.name for p in pentester.permissions} == {
        "engagements.read",
        "engagements.write",
        "findings.read",
        "findings.write",
        "findings.delete",
        "runs.read",
        "runs.write",
        "reports.read",
    }
    assert {p.name for p in viewer.permissions} == {
        "engagements.read",
        "findings.read",
        "reports.read",
    }


@pytest.mark.asyncio
async def test_require_permission_dependency(db_session):
    """`require_permission` must be usable as a FastAPI dependency (direct call here)."""
    from anomaly_api.deps import require_permission

    admin = await _make_user(
        db_session, await _get_role(db_session, RoleName.admin), "admin@example.com", "Admin"
    )
    viewer = await _make_user(
        db_session, await _get_role(db_session, RoleName.client_viewer), "v@example.com", "V"
    )
    await db_session.commit()

    dep = require_permission("runs.write")

    returned = await dep(user=admin)
    assert returned is admin

    with pytest.raises(HTTPException) as exc_info:
        await dep(user=viewer)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_client_viewer_cannot_manage_playbooks_or_schedules(client, db_session):
    from anomaly_core.models import CronSchedule, Playbook

    owner = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.admin),
        "owner-pb-sched@example.com",
        "Owner",
    )
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "viewer-pb-sched@example.com",
        "Viewer",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    playbook = Playbook(engagement_id=eng.id, name="PB", description="")
    schedule = CronSchedule(
        engagement_id=eng.id,
        cron_expression="0 * * * *",
        tool="nmap",
        targets=[],
        params={},
        is_active=True,
    )
    db_session.add_all([playbook, schedule])
    await db_session.commit()

    headers = {
        "Authorization": f"Bearer {create_access_token(viewer.id, [RoleName.client_viewer.value])}"
    }

    # Read/list allowed for engagement-scoped resources where viewer access is permitted.
    resp = await client.get(f"/api/engagements/{eng.id}/playbooks", headers=headers)
    assert resp.status_code == 200
    resp = await client.get(
        f"/api/engagements/{eng.id}/playbooks/{playbook.id}", headers=headers
    )
    assert resp.status_code == 200
    resp = await client.get(f"/api/engagements/{eng.id}/schedules", headers=headers)
    assert resp.status_code == 200

    # Mutations/execution require pentester+.
    resp = await client.post(
        f"/api/engagements/{eng.id}/playbooks",
        headers=headers,
        json={"name": "x", "description": "", "steps": []},
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/engagements/{eng.id}/playbooks/{playbook.id}/execute",
        headers=headers,
        json={"targets": ["in.scope.test"]},
    )
    assert resp.status_code == 403

    resp = await client.delete(
        f"/api/engagements/{eng.id}/playbooks/{playbook.id}",
        headers=headers,
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/engagements/{eng.id}/schedules",
        headers=headers,
        json={
            "cron_expression": "0 1 * * *",
            "tool": "nmap",
            "targets": [],
            "params": {},
            "is_active": True,
        },
    )
    assert resp.status_code == 403

    resp = await client.delete(
        f"/api/engagements/{eng.id}/schedules/{schedule.id}",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_engagement_submit_and_approve_role_enforcement(client, db_session):
    owner = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.admin),
        "owner-submit-approve@example.com",
        "Owner",
    )
    pentester = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.pentester),
        "pentester-submit-approve@example.com",
        "Pentester",
    )
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "viewer-submit-approve@example.com",
        "Viewer",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=pentester.id, role=RoleName.pentester)
    )
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    await db_session.commit()

    owner_headers = {
        "Authorization": f"Bearer {create_access_token(owner.id, [RoleName.admin.value])}"
    }
    pentester_headers = {
        "Authorization": f"Bearer {create_access_token(pentester.id, [RoleName.pentester.value])}"
    }
    viewer_headers = {
        "Authorization": f"Bearer {create_access_token(viewer.id, [RoleName.client_viewer.value])}"
    }

    # Viewer cannot submit or approve.
    assert (
        await client.post(f"/api/engagements/{eng.id}/submit", headers=viewer_headers)
    ).status_code == 403
    assert (
        await client.post(f"/api/engagements/{eng.id}/approve", headers=viewer_headers)
    ).status_code == 403

    # Pentester can submit but cannot approve.
    resp = await client.post(f"/api/engagements/{eng.id}/submit", headers=pentester_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_approval"

    resp = await client.post(f"/api/engagements/{eng.id}/approve", headers=pentester_headers)
    assert resp.status_code == 403

    # Admin can approve.
    resp = await client.post(f"/api/engagements/{eng.id}/approve", headers=owner_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body.get("approved_by") == str(owner.id)


@pytest.mark.asyncio
async def test_client_viewer_cannot_modify_engagement_scope_or_targets(client, db_session):
    owner = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.admin),
        "owner-scope-target@example.com",
        "Owner",
    )
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "viewer-scope-target@example.com",
        "Viewer",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    await db_session.commit()

    headers = {
        "Authorization": f"Bearer {create_access_token(viewer.id, [RoleName.client_viewer.value])}"
    }

    resp = await client.put(
        f"/api/engagements/{eng.id}/scope",
        headers=headers,
        json={"entries": [{"kind": "in", "target_value": "example.com"}]},
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/engagements/{eng.id}/targets",
        headers=headers,
        json={"value": "example.com", "type": "domain"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_only_global_endpoints(client, db_session):
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "viewer-admin-edges@example.com",
        "Viewer",
    )
    await db_session.commit()
    headers = {
        "Authorization": f"Bearer {create_access_token(viewer.id, [RoleName.client_viewer.value])}"
    }

    # Global admin-only surfaces
    assert (await client.get("/api/users", headers=headers)).status_code == 403
    assert (await client.get("/api/audit", headers=headers)).status_code == 403
    assert (await client.get("/api/tags", headers=headers)).status_code == 403
    assert (
        await client.post("/api/tags", headers=headers, json={"name": "x", "color": "#000"})
    ).status_code == 403
    assert (
        await client.post(
            "/api/notifications/broadcast",
            headers=headers,
            json={"title": "t", "message": "m"},
        )
    ).status_code == 403
    assert (await client.get("/api/webhooks", headers=headers)).status_code == 403
    assert (
        await client.post("/api/webhooks", headers=headers, json={"url": "https://example.com"})
    ).status_code == 403
