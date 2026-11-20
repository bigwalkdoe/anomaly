from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_engagement_crud_and_scope_update(client, db_session):
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
        json={"name": "E1", "mode": "bug_bounty"},
    )
    assert resp.status_code == 201
    eng_id = resp.json()["id"]

    resp = await client.get(
        f"/api/engagements/{eng_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    resp = await client.patch(
        f"/api/engagements/{eng_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "active"},
    )
    assert resp.status_code == 200

    resp = await client.put(
        f"/api/engagements/{eng_id}/scope",
        headers={"Authorization": f"Bearer {token}"},
        json={"entries": [{"kind": "in", "target_value": "example.com"}]},
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/engagements/{eng_id}/targets",
        headers={"Authorization": f"Bearer {token}"},
        json={"value": "example.com", "type": "domain"},
    )
    assert resp.status_code in (200, 201)

    resp = await client.delete(
        f"/api/engagements/{eng_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_patch_approval_requires_admin_and_sets_audit_metadata(client, db_session):
    from anomaly_core.models import AuditLog, Engagement, EngagementMember, EngagementMode

    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
        await db_session.flush()

    admin = User(
        email="admin-approve@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    pentester = User(
        email="pentester-approve@example.com",
        name="Pentester",
        password_hash=hash_password("pass"),
        roles=[pentester_role],
    )
    db_session.add_all([admin, pentester])
    await db_session.flush()

    eng = Engagement(
        name="Approval Governance",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
    )
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=pentester.id, role=RoleName.pentester)
    )
    await db_session.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id, ['admin'])}"}
    pentester_headers = {
        "Authorization": f"Bearer {create_access_token(pentester.id, ['pentester'])}"
    }

    # Pentester cannot approve via PATCH (governed approval path requires admin).
    resp = await client.patch(
        f"/api/engagements/{eng.id}",
        headers=pentester_headers,
        json={"status": "approved"},
    )
    assert resp.status_code == 403

    # Admin PATCH-to-approved is allowed and records approval metadata/audit.
    resp = await client.patch(
        f"/api/engagements/{eng.id}",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body.get("approved_by") == str(admin.id)
    assert body.get("approved_at")

    approval_log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id,
            AuditLog.action == "engagement.approve",
        )
    )
    assert approval_log is not None
    assert (approval_log.metadata or {}).get("approver_id") == str(admin.id)
