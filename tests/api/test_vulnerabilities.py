from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMode,
    Finding,
    FindingSeverity,
    Role,
    RoleName,
    User,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_vulnerability_summary(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    owner = User(
        email="owner@example.com",
        name="Owner",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    for sev in ["critical", "high", "medium", "low"]:
        f = Finding(
            engagement_id=eng.id,
            title=f"Finding {sev}",
            severity=FindingSeverity(sev),
            description="desc",
            reporter_id=owner.id,
            fingerprint=f"fp_{sev}",
        )
        db_session.add(f)
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    resp = await client.get(
        "/api/vulnerabilities/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["critical"] == 1
