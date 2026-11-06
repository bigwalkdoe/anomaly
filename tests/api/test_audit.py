from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    AuditLog,
    Engagement,
    EngagementMember,
    EngagementMode,
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
async def test_scope_warning_writes_audit_row(client, db_session):
    from anomaly_core.auth import create_access_token

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
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"tool": "nmap", "targets": ["evil.com"]},
    )
    # Should be enqueued but with scope warning logged
    assert resp.status_code in (200, 201, 202)
    log = await db_session.scalar(select(AuditLog).where(AuditLog.action == "scope.warning"))
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
    assert resp2.status_code == 403
