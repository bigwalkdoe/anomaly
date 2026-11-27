from __future__ import annotations

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
    """Review Focus #2/#3: unapproved or out-of-scope assessment requests denied.

    Denials must be audited and there must be no bypass.
    """
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
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.test")
    )
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
        appr = await client.patch(
            f"/api/engagements/{eng.id}", headers=oh, json={"status": "approved"}
        )
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
            AuditLog.action.in_(
                ["policy.denied", "assessment.denied", "run.denied", "scope.denied"]
            ),
        )
    )
    assert deny_audit is not None


async def _seed_policy_engagement(db, owner_email, pt_email, status=EngagementStatus.approved):
    owner = await _seed(db, owner_email, RoleName.admin)
    pt = await _seed(db, pt_email, RoleName.pentester)
    eng = Engagement(
        name=f"Policy {owner_email}",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        status=status,
    )
    db.add(eng)
    await db.flush()
    db.add(EngagementMember(engagement_id=eng.id, user_id=pt.id, role=RoleName.pentester))
    scope = Scope(engagement_id=eng.id)
    db.add(scope)
    await db.flush()
    db.add(ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="allowed.test"))
    await db.commit()
    return pt, eng


@pytest.mark.asyncio
async def test_allowed_assessment_records_policy_allowed_audit(client, db_session):
    pt, eng = await _seed_policy_engagement(
        db_session, "policy-allow-owner@example.com", "policy-allow-pt@example.com"
    )
    headers = {"Authorization": f"Bearer {create_access_token(pt.id, [RoleName.pentester.value])}"}

    response = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )

    assert response.status_code == 202
    run = await db_session.scalar(select(Run).where(Run.engagement_id == eng.id))
    assert run is not None
    execution_policy = run.params["execution_manifest"]["execution_policy"]
    assert execution_policy["allowed"] is True
    assert execution_policy["targets"] == ["allowed.test"]
    log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id, AuditLog.action == "policy.allowed"
        )
    )
    assert log is not None
    assert log.metadata["allowed"] is True
    assert log.metadata["reason"] is None
    assert log.metadata["op"] == "assessment.request"
    assert log.metadata["source"] == "api.legacy"
    assert log.metadata["targets"] == ["allowed.test"]
    assert log.metadata["in_scope"] == ["allowed.test"]
    assert log.metadata["out_of_scope"] == []
    assert log.metadata["has_warning"] is False


@pytest.mark.asyncio
async def test_out_of_scope_assessment_denial_records_scope_context(client, db_session):
    pt, eng = await _seed_policy_engagement(
        db_session, "policy-scope-owner@example.com", "policy-scope-pt@example.com"
    )
    headers = {"Authorization": f"Bearer {create_access_token(pt.id, [RoleName.pentester.value])}"}

    response = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["evil.outside.test"]},
    )

    assert response.status_code == 403
    log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id, AuditLog.action == "policy.denied"
        )
    )
    assert log is not None
    assert log.metadata["allowed"] is False
    assert log.metadata["reason"] == "out_of_scope"
    assert log.metadata["targets"] == ["evil.outside.test"]
    assert log.metadata["out_of_scope"] == ["evil.outside.test"]
    assert log.metadata["has_warning"] is True
    assert log.metadata["source"] == "api.legacy"


@pytest.mark.asyncio
async def test_unapproved_assessment_denial_records_status(client, db_session):
    pt, eng = await _seed_policy_engagement(
        db_session,
        "policy-draft-owner@example.com",
        "policy-draft-pt@example.com",
        status=EngagementStatus.draft,
    )
    headers = {"Authorization": f"Bearer {create_access_token(pt.id, [RoleName.pentester.value])}"}

    response = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )

    assert response.status_code == 403
    log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id, AuditLog.action == "policy.denied"
        )
    )
    assert log is not None
    assert log.metadata["allowed"] is False
    assert log.metadata["reason"] == "engagement_not_approved"
    assert log.metadata["status"] == "draft"
    assert log.metadata["op"] == "assessment.request"
    assert log.metadata["source"] == "api.legacy"


@pytest.mark.asyncio
async def test_v1_allowed_assessment_records_policy_allowed_audit_with_source(client, db_session):
    pt, eng = await _seed_policy_engagement(
        db_session, "policy-v1-owner@example.com", "policy-v1-pt@example.com"
    )
    headers = {"Authorization": f"Bearer {create_access_token(pt.id, [RoleName.pentester.value])}"}

    response = await client.post(
        f"/api/v1/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"], "params": {}},
    )

    assert response.status_code == 202
    log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.engagement_id == eng.id, AuditLog.action == "policy.allowed"
        )
    )
    assert log is not None
    assert log.metadata["allowed"] is True
    assert log.metadata["source"] == "api.v1"
