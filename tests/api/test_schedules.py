from __future__ import annotations

import pytest
from sqlalchemy import select

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import CronSchedule, Engagement, EngagementMode, Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_and_list_schedules(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    owner = User(email="owner@example.com", name="Owner", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/schedules",
        headers={"Authorization": f"Bearer {token}"},
        json={"cron_expression": "0 2 * * *", "tool": "nmap", "targets": ["example.com"], "is_active": True},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["cron_expression"] == "0 2 * * *"
    assert body["tool"] == "nmap"
    assert body["targets"] == ["example.com"]

    resp2 = await client.get(
        f"/api/engagements/{eng.id}/schedules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
