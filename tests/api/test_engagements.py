from __future__ import annotations

import pytest

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Engagement, EngagementMember, EngagementMode, Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_engagement_crud_and_scope_update(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(email="admin@example.com", name="Admin", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.post("/api/engagements", headers={"Authorization": f"Bearer {token}"}, json={"name": "E1", "mode": "bug_bounty"})
    assert resp.status_code == 201
    eng_id = resp.json()["id"]

    resp = await client.get(f"/api/engagements/{eng_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    resp = await client.patch(f"/api/engagements/{eng_id}", headers={"Authorization": f"Bearer {token}"}, json={"status": "active"})
    assert resp.status_code == 200

    resp = await client.put(f"/api/engagements/{eng_id}/scope", headers={"Authorization": f"Bearer {token}"}, json={"entries": [{"kind": "in", "target_value": "example.com"}]})
    assert resp.status_code == 200

    resp = await client.post(f"/api/engagements/{eng_id}/targets", headers={"Authorization": f"Bearer {token}"}, json={"value": "example.com", "type": "domain"})
    assert resp.status_code in (200, 201)

    resp = await client.delete(f"/api/engagements/{eng_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 204)
