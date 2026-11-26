from __future__ import annotations

import uuid

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMode,
    Membership,
    Organization,
    Role,
    RoleName,
    User,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_v1_admin_list_engagements_scopes_to_org_when_org_exists(client, db_session):
    """Admin listing must only include engagements from orgs they belong to (plus unscoped)."""
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email="v1admin@example.com",
        name="V1 Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.flush()

    org = Organization(name="V1 Org", slug=f"v1-org-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    eng = Engagement(
        name="V1 Eng",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org.id,
    )
    eng_unscoped = Engagement(
        name="V1 Unscoped Eng",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=None,
    )
    db_session.add_all([eng, eng_unscoped])
    await db_session.flush()

    # A different tenant's engagement must not leak into the admin's list.
    other_owner = User(
        email="v1other@example.com",
        name="V1 Other",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(other_owner)
    await db_session.flush()
    other_org = Organization(name="V1 Other Org", slug=f"v1-other-org-{uuid.uuid4().hex[:8]}")
    db_session.add(other_org)
    await db_session.flush()
    db_session.add(Membership(user_id=other_owner.id, organization_id=other_org.id, role="owner"))
    eng_other = Engagement(
        name="V1 Other Eng",
        mode=EngagementMode.own_infra,
        owner_id=other_owner.id,
        organization_id=other_org.id,
    )
    db_session.add(eng_other)
    await db_session.commit()

    token = create_access_token(admin.id, [RoleName.admin.value])
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/engagements", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    ids = [e["id"] for e in data]
    assert str(eng.id) in ids
    assert str(eng_unscoped.id) in ids
    assert str(eng_other.id) not in ids
