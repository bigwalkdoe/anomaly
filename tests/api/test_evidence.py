from __future__ import annotations

import pytest

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Evidence, EvidenceType, Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_list_evidence(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(email="admin@example.com", name="Admin", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(admin.id, ["admin"])
    resp = await client.get("/api/evidence", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
