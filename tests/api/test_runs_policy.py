from __future__ import annotations

import uuid

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
    Scope,
    ScopeEntry,
    ScopeEntryKind,
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
async def test_assessment_requires_approval_and_scope_policy(client, db_session, monkeypatch):
    """Review Focus #2/#3: unapproved or out-of-scope assessment requests denied and audited; no bypass."""
    monkeypatch.setenv("RUNNER_MODE", "inline")
    owner = await _seed(db_session, "policy-owner@example.com", RoleName.admin)
    pt = await _seed(db_session, "policy-pt@example.com", RoleName.pentester)
    eng = Engagement(name="PolicyEng", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=pt.id, role=RoleName.pentester))
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.test"))
    await db_session.commit()

    token = create_access_token(pt.id, [RoleName.pentester.value])
    headers = {"Authorization": f"Bearer {token}"}

    # Not approved -> must be denied (not merely warned)
    r = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )
    assert r.status_code in (400, 403, 409), r.text

    # Approve engagement via available mechanism
    owner_token = create_access_token(owner.id, [RoleName.admin.value])
    oh = {"Authorization": f"Bearer {owner_token}"}
    appr = await client.post(f"/api/engagements/{eng.id}/approve", headers=oh, json={})
    if appr.status_code == 404:
        appr = await client.patch(f"/api/engagements/{eng.id}", headers=oh, json={"status": "approved"})
    assert appr.status_code == 200

    # Out-of-scope -> denied (policy/scope enforcement, no bypass)
    r2 = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["evil.outside.test"]},
    )
    assert r2.status_code in (400, 403, 422), r2.text

    deny_audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id,
            AuditLog.action.in_(["policy.denied", "assessment.denied", "run.denied", "scope.denied"]),
        )
    )
    assert deny_audit is not None
