from __future__ import annotations

import anomaly_api.assessment
import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    AuditLog,
    Engagement,
    EngagementMember,
    EngagementMode,
    EngagementStatus,
    Role,
    RoleName,
    Run,
    Scope,
    ScopeEntry,
    ScopeEntryKind,
    User,
)
from sqlalchemy import func, select


async def _role(db_session, name: RoleName) -> Role:
    role = await db_session.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=name.value)
        db_session.add(role)
        await db_session.flush()
    return role


async def _user(db_session, email: str, role: Role) -> User:
    user = User(
        email=email,
        name=email.split("@")[0],
        password_hash=hash_password("pass"),
        roles=[role],
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_engagement(db_session, email: str) -> tuple[User, Engagement]:
    admin_role = await _role(db_session, RoleName.admin)
    pentester_role = await _role(db_session, RoleName.pentester)
    owner = await _user(db_session, f"owner-{email}", admin_role)
    pt = await _user(db_session, email, pentester_role)

    eng = Engagement(
        name=f"Idempotency {email}",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=EngagementStatus.approved,
    )
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=pt.id, role=RoleName.pentester))
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.test")
    )
    await db_session.commit()
    return pt, eng


@pytest.mark.asyncio
async def test_legacy_replay_reuses_run_and_audits_replay(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-replay@example.com")
    headers = {
        "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
        "Idempotency-Key": "client-key-1",
    }
    body = {"tool": "stub", "targets": ["allowed.test"]}

    first = await client.post(f"/api/engagements/{eng.id}/runs", headers=headers, json=body)
    second = await client.post(f"/api/engagements/{eng.id}/runs", headers=headers, json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["idempotent_replay"] is True
    runs = (await db_session.scalars(select(Run).where(Run.engagement_id == eng.id))).all()
    assert len(runs) == 1
    enqueues = (
        await db_session.scalars(select(AuditLog).where(AuditLog.action == "run.enqueue"))
    ).all()
    assert len(enqueues) == 1
    replay = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "run.idempotent_replay")
    )
    assert replay is not None
    assert replay.metadata["idempotency_key_hash"] == (
        "64dbdc38ede19b85cac8beccc15d52debb1a30e42c2fa15716ce95ac0913ad09"
    )
    assert "client-key-1" not in str(replay.metadata)


@pytest.mark.asyncio
async def test_blank_and_oversized_idempotency_keys_are_rejected(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-invalid-key@example.com")
    base = {"Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}"}
    body = {"tool": "stub", "targets": ["allowed.test"]}

    blank = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={**base, "Idempotency-Key": "   "},
        json=body,
    )
    oversized = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={**base, "Idempotency-Key": "x" * 256},
        json=body,
    )

    assert blank.status_code == 400
    assert oversized.status_code == 400
    assert (await db_session.scalar(select(func.count()).select_from(Run))) == 0


@pytest.mark.asyncio
async def test_idempotency_key_is_scoped_to_engagement_and_user(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-scope@example.com")
    pt2, eng2 = await _seed_engagement(db_session, "legacy-scope-2@example.com")
    db_session.add(
        EngagementMember(engagement_id=eng2.id, user_id=pt.id, role=RoleName.pentester)
    )
    db_session.add(
        EngagementMember(engagement_id=eng.id, user_id=pt2.id, role=RoleName.pentester)
    )
    await db_session.commit()
    body = {"tool": "stub", "targets": ["allowed.test"]}

    first = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )
    other_eng = await client.post(
        f"/api/engagements/{eng2.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )
    other_user = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt2.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )

    assert first.status_code == 202
    assert other_eng.status_code == 202
    assert other_user.status_code == 202
    assert first.json()["idempotent_replay"] is False
    assert other_eng.json()["idempotent_replay"] is False
    assert other_user.json()["idempotent_replay"] is False
    assert len({first.json()["id"], other_eng.json()["id"], other_user.json()["id"]}) == 3


@pytest.mark.asyncio
async def test_duplicate_race_reuses_existing_run(client, db_session, monkeypatch):
    pt, eng = await _seed_engagement(db_session, "legacy-race@example.com")
    key_hash = "4d417b736472e804fd99a8689e537b9a15ab0ea5b048683ffeb577bc6ef3e586"
    headers = {
        "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
        "Idempotency-Key": "race-key",
    }
    first = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )
    existing = await db_session.scalar(
        select(Run).where(Run.idempotency_key_hash == key_hash)
    )
    real_find = anomaly_api.assessment.find_idempotent_run
    calls = 0

    async def miss_then_find(*args, **kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_find(*args, **kwargs)

    monkeypatch.setattr(anomaly_api.assessment, "find_idempotent_run", miss_then_find)

    replay = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )

    assert first.status_code == 202
    assert replay.status_code == 202
    assert replay.json()["id"] == str(existing.id)
    assert replay.json()["idempotent_replay"] is True
    assert calls == 2
