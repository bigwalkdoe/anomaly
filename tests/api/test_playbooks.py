from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMode,
    EngagementStatus,
    Playbook,
    PlaybookStep,
    Role,
    RoleName,
    Scope,
    ScopeEntry,
    ScopeEntryKind,
    User,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_execute_playbook(client, db_session, monkeypatch):
    monkeypatch.setenv("RUNNER_MODE", "inline")
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
    eng = Engagement(
        name="E1",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    )
    pb = Playbook(engagement_id=eng.id, name="Recon Playbook", description="Recon steps")
    db_session.add(pb)
    await db_session.flush()
    db_session.add(
        PlaybookStep(playbook_id=pb.id, name="nmap_scan", tool="nmap", params={}, order=1)
    )
    db_session.add(
        PlaybookStep(playbook_id=pb.id, name="httpx_probe", tool="httpx", params={}, order=2)
    )
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"targets": ["example.com"]},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["runs_created"] == 2
    assert "Recon Playbook" in body["message"]


@pytest.mark.asyncio
async def test_playbook_endpoints_require_playbook_to_belong_to_engagement(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("RUNNER_MODE", "inline")
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    owner = User(
        email="owner2@example.com",
        name="Owner2",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(owner)
    await db_session.flush()
    eng_a = Engagement(
        name="A",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    eng_b = Engagement(
        name="B",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    db_session.add_all([eng_a, eng_b])
    await db_session.flush()
    for eng in (eng_a, eng_b):
        scope = Scope(engagement_id=eng.id)
        db_session.add(scope)
        await db_session.flush()
        db_session.add(
            ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
        )
    pb_b = Playbook(engagement_id=eng_b.id, name="PB-B", description="in B")
    db_session.add(pb_b)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb_b.id, name="s1", tool="nmap", params={}, order=1))
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access/execute playbook from engagement B via engagement A path
    resp = await client.get(
        f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}",
        headers=headers,
    )
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}/execute",
        headers=headers,
        json={"targets": ["example.com"]},
    )
    assert resp.status_code == 404

    resp = await client.delete(
        f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}",
        headers=headers,
    )
    assert resp.status_code == 404

    # Correct path still works
    resp = await client.post(
        f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}/execute",
        headers=headers,
        json={"targets": ["example.com"]},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["runs_created"] == 1

    # Runs created by execute should carry engagement's organization_id (if any)
    from anomaly_core.models import Run

    runs = (await db_session.scalars(select(Run).where(Run.engagement_id == eng_b.id))).all()
    assert runs
    assert all(
        getattr(r, "organization_id", None) == getattr(eng_b, "organization_id", None) for r in runs
    )


@pytest.mark.asyncio
async def test_execute_playbook_denied_when_engagement_not_approved(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("RUNNER_MODE", "inline")
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    owner = User(
        email="owner3@example.com",
        name="Owner3",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(
        name="DraftEng",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status="draft",
    )
    db_session.add(eng)
    await db_session.flush()
    pb = Playbook(engagement_id=eng.id, name="PB", description="")
    db_session.add(pb)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb.id, name="s1", tool="nmap", params={}, order=1))
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"targets": ["example.com"]},
    )
    assert resp.status_code == 403
    assert (
        "not approved" in resp.json().get("detail", "").lower()
        or "not approved" in resp.text.lower()
    )


@pytest.mark.asyncio
async def test_execute_playbook_denied_when_targets_out_of_scope(client, db_session, monkeypatch):
    monkeypatch.setenv("RUNNER_MODE", "inline")
    from anomaly_core.models import EngagementStatus, Scope, ScopeEntry, ScopeEntryKind

    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    owner = User(
        email="owner4@example.com",
        name="Owner4",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(owner)
    await db_session.flush()
    eng = Engagement(
        name="ApprovedEng",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.example.com")
    )
    pb = Playbook(engagement_id=eng.id, name="PB", description="")
    db_session.add(pb)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb.id, name="s1", tool="nmap", params={}, order=1))
    await db_session.commit()

    token = create_access_token(owner.id, ["admin"])
    resp = await client.post(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"targets": ["evil.example.com"]},
    )
    assert resp.status_code == 403
    assert (
        "out of scope" in resp.json().get("detail", "").lower()
        or "out of scope" in resp.text.lower()
    )


@pytest.mark.asyncio
async def test_playbook_write_and_execute_require_pentester_role(client, db_session, monkeypatch):
    monkeypatch.setenv("RUNNER_MODE", "inline")
    from anomaly_core.models import (
        EngagementMember,
        EngagementStatus,
        RoleName,
        Scope,
        ScopeEntry,
        ScopeEntryKind,
    )

    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    viewer_role = await db_session.scalar(select(Role).where(Role.name == RoleName.client_viewer))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
    if viewer_role is None:
        viewer_role = Role(name=RoleName.client_viewer, description="viewer")
        db_session.add(viewer_role)
    await db_session.flush()
    owner = User(
        email="owner-rbac@example.com",
        name="OwnerRBAC",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    viewer = User(
        email="viewer-rbac@example.com",
        name="ViewerRBAC",
        password_hash=hash_password("pass"),
        roles=[viewer_role],
    )
    db_session.add_all([owner, viewer])
    await db_session.flush()
    eng = Engagement(
        name="EngRBAC",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    db_session.add(eng)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=viewer.id, role=RoleName.client_viewer)
    )
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    )
    pb = Playbook(engagement_id=eng.id, name="PB", description="")
    db_session.add(pb)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb.id, name="s1", tool="nmap", params={}, order=1))
    await db_session.commit()

    token = create_access_token(viewer.id, [RoleName.client_viewer.value])
    headers = {"Authorization": f"Bearer {token}"}

    # viewer can list/read but cannot create/update/delete/execute
    r = await client.get(f"/api/engagements/{eng.id}/playbooks", headers=headers)
    assert r.status_code == 200

    r = await client.get(f"/api/engagements/{eng.id}/playbooks/{pb.id}", headers=headers)
    assert r.status_code == 200

    r = await client.post(
        f"/api/engagements/{eng.id}/playbooks",
        headers=headers,
        json={"name": "X", "description": "", "steps": []},
    )
    assert r.status_code in (403, 404)

    r = await client.patch(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}",
        headers=headers,
        json={"name": "Y"},
    )
    assert r.status_code in (403, 404)

    r = await client.post(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}/execute",
        headers=headers,
        json={"targets": ["example.com"]},
    )
    assert r.status_code in (403, 404)

    r = await client.delete(
        f"/api/engagements/{eng.id}/playbooks/{pb.id}",
        headers=headers,
    )
    assert r.status_code in (403, 404)
