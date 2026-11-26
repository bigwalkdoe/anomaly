from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    Evidence,
    EvidenceType,
    Role,
    RoleName,
    Run,
    RunStatus,
    User,
)
from sqlalchemy import select


async def _seed_admin(db_session, email: str = "admin@example.com") -> User:
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    admin = User(
        email=email,
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest.mark.asyncio
async def test_list_evidence(client, db_session):
    admin = await _seed_admin(db_session)
    await db_session.commit()
    token = create_access_token(admin.id, ["admin"])
    resp = await client.get("/api/evidence", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_evidence_integrity_includes_provenance(client, db_session):
    admin = await _seed_admin(db_session, email="ev-admin@example.com")
    eng = Engagement(name="EvEng", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=admin.id, role=RoleName.admin))
    run = Run(engagement_id=eng.id, user_id=admin.id, tool="nmap", status=RunStatus.succeeded)
    db_session.add(run)
    await db_session.flush()
    ev = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="logs/test.txt",
        sha256="a" * 64,
        collector="worker",
        tool="nmap",
        metadata={"sha256": "a" * 64, "collector": "worker", "tool": "nmap"},
    )
    db_session.add(ev)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(f"/api/evidence/{ev.id}/integrity", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(ev.id)
    assert body["sha256"] == "a" * 64
    assert body["verified"] is True or body["recorded"] is True
    prov = body["provenance"]
    assert prov["engagement_id"] == str(eng.id)
    assert prov["run_id"] == str(run.id)
    assert prov["collector"] == "worker"
    assert prov["tool"] == "nmap"
    assert prov["storage_key"] == "logs/test.txt"


@pytest.mark.asyncio
async def test_evidence_integrity_detects_tampered_metadata_checksum(client, db_session):
    admin = await _seed_admin(db_session, email="ev-tamper@example.com")
    eng = Engagement(name="TamperEng", mode=EngagementMode.own_infra, owner_id=admin.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=admin.id, role=RoleName.admin))
    run = Run(engagement_id=eng.id, user_id=admin.id, tool="nmap", status=RunStatus.succeeded)
    db_session.add(run)
    await db_session.flush()
    ev = Evidence(
        engagement_id=eng.id,
        run_id=run.id,
        type=EvidenceType.log,
        storage_key="logs/tampered.txt",
        sha256="a" * 64,
        collector="worker",
        tool="nmap",
        metadata={
            "sha256": "b" * 64,
            "stdout": "hello",
            "stderr": "",
            "collector": "worker",
            "tool": "nmap",
        },
    )
    db_session.add(ev)
    await db_session.commit()

    token = create_access_token(admin.id, ["admin"])
    resp = await client.get(
        f"/api/evidence/{ev.id}/integrity", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is False
    assert body["verification"] == "inconsistent"
    assert body["sha256"] == "a" * 64
    assert body["metadata_sha256"] == "b" * 64
