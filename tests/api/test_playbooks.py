from __future__ import annotations

import os

import pytest

from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Engagement, EngagementMode, Playbook, PlaybookStep, Role, RoleName, User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_execute_playbook(client, db_session, monkeypatch):
    monkeypatch.setenv("RUNNER_MODE", "inline")
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
    await db_session.flush()
    pb = Playbook(engagement_id=eng.id, name="Recon Playbook", description="Recon steps")
    db_session.add(pb)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb.id, name="nmap_scan", tool="nmap", params={}, order=1))
    db_session.add(PlaybookStep(playbook_id=pb.id, name="httpx_probe", tool="httpx", params={}, order=2))
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
