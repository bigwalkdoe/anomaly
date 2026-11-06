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
async def test_enqueue_run_scope_warning_and_status(client, db_session, monkeypatch):
    monkeypatch.setenv("RUNNER_MODE", "inline")
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
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=p.id, role=RoleName.pentester))
    await db_session.commit()

    token = create_access_token(p.id, ["pentester"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"tool": "nmap", "targets": ["evil.com"]},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "id" in body

    status_resp = await client.get(
        f"/api/runs/{body['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["scope_warning"] is True

    log = await db_session.scalar(select(AuditLog).where(AuditLog.action == "run.enqueue"))
    assert log is not None
