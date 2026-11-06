from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Engagement, EngagementMember, EngagementMode, Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_finding_crud_and_status_transition(client, db_session):
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
        f"/api/engagements/{eng.id}/findings",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "SQLi", "severity": "high", "description": "desc"},
    )
    assert resp.status_code == 201
    finding_id = resp.json()["id"]

    resp = await client.get(
        f"/api/engagements/{eng.id}/findings", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    resp = await client.get(
        f"/api/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    resp = await client.patch(
        f"/api/findings/{finding_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "triaged"},
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/findings/{finding_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200

    resp = await client.delete(
        f"/api/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code in (200, 204)
