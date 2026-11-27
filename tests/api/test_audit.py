from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    AuditLog,
    Engagement,
    EngagementMember,
    EngagementMode,
    Membership,
    Organization,
    Role,
    RoleName,
    User,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_creating_engagement_writes_audit_row(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="admin@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.post(
        "/api/engagements",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "E1", "mode": "own_infra"},
    )
    assert resp.status_code == 201
    count = await db_session.scalar(select(__import__("sqlalchemy").func.count(AuditLog.id)))
    assert count and count > 0


@pytest.mark.asyncio
async def test_scope_policy_denial_writes_audit_row(client, db_session):
    from anomaly_core.auth import create_access_token
    from anomaly_core.models import EngagementStatus, Scope, ScopeEntry, ScopeEntryKind

    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="admin@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.flush()
    eng = Engagement(
        name="E1",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        status=EngagementStatus.approved,
    )
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.com")
    )
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"tool": "nmap", "targets": ["evil.com"]},
    )
    # Out-of-scope request must be denied by policy and audited
    assert resp.status_code == 403
    log = await db_session.scalar(select(AuditLog).where(AuditLog.action == "policy.denied"))
    assert log is not None


@pytest.mark.asyncio
async def test_audit_list_filters_and_respects_access(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
    await db_session.flush()

    owner = User(
        email="owner@example.com",
        name="Owner",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(owner)
    await db_session.flush()
    p = User(
        email="p@example.com", name="P", password_hash=hash_password("pass"), roles=[pentester_role]
    )
    db_session.add(p)
    await db_session.flush()

    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=p.id, role=RoleName.pentester))
    await db_session.commit()

    token = create_access_token(p.id, ["pentester"])
    resp = await client.get(
        f"/api/audit?engagement_id={eng1.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    resp2 = await client.get(
        f"/api/audit?engagement_id={eng2.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp2.status_code in (403, 404)


@pytest.mark.asyncio
async def test_engagement_audit_rejects_client_viewer_member(client, db_session):
    """The break: engagement-scoped audit logs were readable by client viewers."""
    viewer_role = await db_session.scalar(select(Role).where(Role.name == RoleName.client_viewer))
    if viewer_role is None:
        viewer_role = Role(name=RoleName.client_viewer, description="client_viewer")
        db_session.add(viewer_role)
        await db_session.flush()
    viewer = User(
        email="audit-viewer@example.com",
        name="Viewer",
        password_hash=hash_password("pass"),
        roles=[viewer_role],
    )
    db_session.add(viewer)
    await db_session.flush()

    org = Organization(name="Audit Viewer Org", slug="audit-viewer-org")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=viewer.id, organization_id=org.id, role="member"))

    engagement = Engagement(
        name="Audit Viewer Engagement",
        mode=EngagementMode.own_infra,
        owner_id=viewer.id,
        organization_id=org.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(
            engagement_id=engagement.id, user_id=viewer.id, role=RoleName.client_viewer
        )
    )
    await db_session.commit()

    token = create_access_token(viewer.id, ["client_viewer"])
    resp = await client.get(
        f"/api/audit?engagement_id={engagement.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_engagement_audit_hides_foreign_org_logs(client, db_session):
    """The break: engagement audit reads trusted engagement_id over child org consistency."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="audit-org-admin@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.flush()

    org_a = Organization(name="Audit Consistency Org A", slug="audit-consistency-org-a")
    org_b = Organization(name="Audit Consistency Org B", slug="audit-consistency-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    engagement = Engagement(
        name="Audit Org Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org_a.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )
    db_session.add_all(
        [
            AuditLog(
                actor_id=admin.id,
                action="audit.consistent",
                resource_type="test",
                engagement_id=engagement.id,
                organization_id=org_a.id,
                metadata_={"marker": "consistent"},
            ),
            AuditLog(
                actor_id=admin.id,
                action="audit.foreign",
                resource_type="test",
                engagement_id=engagement.id,
                organization_id=org_b.id,
                metadata_={"marker": "foreign"},
            ),
        ]
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, ['admin'])}"}
    scoped = await client.get(f"/api/audit?engagement_id={engagement.id}", headers=headers)
    assert scoped.status_code == 200
    markers = [entry["metadata"].get("marker") for entry in scoped.json()]
    assert "consistent" in markers
    assert "foreign" not in markers

    glob = await client.get("/api/audit", headers=headers)
    assert glob.status_code == 200
    global_markers = [entry["metadata"].get("marker") for entry in glob.json()]
    assert "consistent" in global_markers
    assert "foreign" not in global_markers
