from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
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


async def _seed(db, email, role):
    r = await db.scalar(select(Role).where(Role.name == role))
    if r is None:
        r = Role(name=role, description=role.value)
        db.add(r)
        await db.flush()
    u = User(email=email, name=email, password_hash=hash_password("pass"), roles=[r])
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_cross_tenant_authorization_regression(client, db_session):
    """Review Focus #1: cross-tenant access must be denied without leaking existence."""
    admin = await _seed(db_session, "tenant-admin-a@example.com", RoleName.admin)
    other = await _seed(db_session, "tenant-admin-b@example.com", RoleName.admin)
    await db_session.flush()

    org_a = Organization(name="Org A", slug="org-a-tenant")
    org_b = Organization(name="Org B", slug="org-b-tenant")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=other.id, organization_id=org_b.id, role="owner"))

    eng_a = Engagement(
        name="Eng A", mode=EngagementMode.own_infra, owner_id=admin.id, organization_id=org_a.id
    )
    eng_b = Engagement(
        name="Eng B", mode=EngagementMode.own_infra, owner_id=other.id, organization_id=org_b.id
    )
    db_session.add_all([eng_a, eng_b])
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng_a.id, user_id=admin.id, role=RoleName.admin))
    db_session.add(EngagementMember(engagement_id=eng_b.id, user_id=other.id, role=RoleName.admin))
    await db_session.commit()

    token_a = create_access_token(admin.id, [RoleName.admin.value])
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A must not access engagement B
    r = await client.get(f"/api/engagements/{eng_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    # If tenant context is explicit, listing must not include other tenant's engagement
    lst = await client.get("/api/engagements", headers=headers_a)
    assert lst.status_code == 200
    ids = [e["id"] for e in lst.json()]
    assert str(eng_b.id) not in ids
