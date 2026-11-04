from __future__ import annotations

import pytest
from fastapi import HTTPException

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
            EngagementMember(
                engagement_id=engagement.id, user_id=user.id, role=membership_role
            )
        )
    await db_session.flush()
    return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, ['pentester'])}"}


@pytest.mark.asyncio
async def test_admin_can_access_any_engagement(client, db_session):
    admin = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "admin@example.com", "Admin")
    eng = Engagement(name="Test", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.commit()

    resp = await client.get(f"/api/engagements/{eng.id}", headers=_auth(admin))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pentester_can_access_assigned_engagements_only(client, db_session):
    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    pentester = await _make_user(db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P")
    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=pentester.id, role=RoleName.pentester))
    await db_session.commit()

    resp1 = await client.get(f"/api/engagements/{eng1.id}", headers=_auth(pentester))
    assert resp1.status_code == 200
    resp2 = await client.get(f"/api/engagements/{eng2.id}", headers=_auth(pentester))
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_client_viewer_no_runs_and_no_create(client, db_session):
    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    viewer = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.client_viewer),
        "v@example.com",
        "V",
    )
    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer))
    await db_session.commit()

    headers = _auth(viewer)
    # read findings/reports is allowed
    resp_findings = await client.get(f"/api/engagements/{eng.id}/findings", headers=headers)
    assert resp_findings.status_code == 200
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


@pytest.mark.asyncio
async def test_unassigned_user_gets_403_on_engagement_endpoints(client, db_session):
    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    other = await _make_user(db_session, await _get_role(db_session, RoleName.pentester), "o@example.com", "O")
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    resp = await client.get(f"/api/engagements/{eng.id}", headers=_auth(other))
    assert resp.status_code == 403
    resp_runs = await client.get(f"/api/engagements/{eng.id}/runs", headers=_auth(other))
    assert resp_runs.status_code == 403
    resp_findings = await client.get(f"/api/engagements/{eng.id}/findings", headers=_auth(other))
    assert resp_findings.status_code == 403


@pytest.mark.asyncio
async def test_cross_engagement_finding_read_returns_404(client, db_session):
    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    p = await _make_user(db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P")
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
    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    viewer = await _make_user(db_session, await _get_role(db_session, RoleName.client_viewer), "v2@example.com", "V2")
    eng1 = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=viewer.id, role=RoleName.client_viewer))
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

    owner = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "owner@example.com", "Owner")
    p = await _make_user(db_session, await _get_role(db_session, RoleName.pentester), "p@example.com", "P")
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

    admin = await _make_user(db_session, await _get_role(db_session, RoleName.admin), "admin@example.com", "Admin")
    viewer = await _make_user(db_session, await _get_role(db_session, RoleName.client_viewer), "v@example.com", "V")
    await db_session.commit()

    dep = require_permission("runs.write")

    returned = await dep(user=admin)
    assert returned is admin

    with pytest.raises(HTTPException) as exc_info:
        await dep(user=viewer)
    assert exc_info.value.status_code == 403
