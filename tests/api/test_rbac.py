from __future__ import annotations

import pytest

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    Finding,
    FindingSeverity,
    FindingStatus,
    Role,
    RoleName,
    User,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_admin_can_access_any_engagement(client, db_session):
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

    eng = Engagement(name="Test", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.get(f"/api/engagements/{eng.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pentester_can_access_assigned_engagements_only(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
    await db_session.flush()

    owner = User(email="owner@example.com", name="Owner", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(owner)
    await db_session.flush()

    pentester = User(email="p@example.com", name="P", password_hash=hash_password("pass"), roles=[pentester_role])
    db_session.add(pentester)
    await db_session.flush()

    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()

    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=pentester.id, role=RoleName.pentester))
    await db_session.commit()

    token = create_access_token(pentester.id, ["pentester"])
    resp1 = await client.get(f"/api/engagements/{eng1.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 200
    resp2 = await client.get(f"/api/engagements/{eng2.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_client_viewer_read_only(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    client_role = await db_session.scalar(select(Role).where(Role.name == RoleName.client_viewer))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if client_role is None:
        client_role = Role(name=RoleName.client_viewer, description="client")
        db_session.add(client_role)
    await db_session.flush()

    owner = User(email="owner@example.com", name="Owner", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(owner)
    await db_session.flush()

    viewer = User(email="v@example.com", name="V", password_hash=hash_password("pass"), roles=[client_role])
    db_session.add(viewer)
    await db_session.flush()

    eng = Engagement(name="E1", mode=EngagementMode.client, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()

    db_session.add(EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer))
    await db_session.commit()

    token = create_access_token(viewer.id, ["client_viewer"])
    # read findings/reports allowed
    resp = await client.get(f"/api/engagements/{eng.id}/findings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # no runs, no create - creating run/findings should be forbidden
    resp_create = await client.post(
        f"/api/engagements/{eng.id}/findings",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "x", "severity": "high", "description": "d"},
    )
    assert resp_create.status_code == 403


@pytest.mark.asyncio
async def test_unassigned_user_gets_403_on_engagement_endpoints(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
    await db_session.flush()

    owner = User(email="owner@example.com", name="Owner", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(owner)
    await db_session.flush()

    other = User(email="o@example.com", name="O", password_hash=hash_password("pass"), roles=[pentester_role])
    db_session.add(other)
    await db_session.flush()

    eng = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    token = create_access_token(other.id, ["pentester"])
    resp = await client.get(f"/api/engagements/{eng.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_engagement_finding_read_returns_404(client, db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    pentester_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if pentester_role is None:
        pentester_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(pentester_role)
    await db_session.flush()

    owner = User(email="owner@example.com", name="Owner", password_hash=hash_password("pass"), roles=[admin_role])
    db_session.add(owner)
    await db_session.flush()

    p = User(email="p@example.com", name="P", password_hash=hash_password("pass"), roles=[pentester_role])
    db_session.add(p)
    await db_session.flush()

    eng1 = Engagement(name="E1", mode=EngagementMode.own_infra, owner_id=owner.id)
    eng2 = Engagement(name="E2", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add_all([eng1, eng2])
    await db_session.flush()

    db_session.add(EngagementMember(engagement_id=eng1.id, user_id=p.id, role=RoleName.pentester))
    finding = Finding(
        engagement_id=eng2.id,
        title="x",
        severity=FindingSeverity.high,
        description="d",
        reporter_id=owner.id,
        fingerprint="fp1",
    )
    db_session.add(finding)
    await db_session.commit()

    token = create_access_token(p.id, ["pentester"])
    resp = await client.get(f"/api/findings/{finding.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
