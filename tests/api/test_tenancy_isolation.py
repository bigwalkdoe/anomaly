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


@pytest.mark.asyncio
async def test_cross_tenant_isolation_across_hardened_surfaces(client, db_session):
    """Cross-tenant access must be denied/hidden across reports, evidence, ws, and aggregates."""
    from anomaly_core.models import (
        Evidence,
        EvidenceType,
        Finding,
        FindingSeverity,
        FindingStatus,
        Run,
        RunStatus,
    )

    admin_a = await _seed(db_session, "iso-admin-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "iso-admin-b@example.com", RoleName.admin)

    org_a = Organization(name="Iso Org A", slug="iso-org-a")
    org_b = Organization(name="Iso Org B", slug="iso-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_a = Engagement(
        name="Iso Eng A",
        mode=EngagementMode.own_infra,
        owner_id=admin_a.id,
        organization_id=org_a.id,
    )
    eng_b = Engagement(
        name="Iso Eng B",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
    )
    db_session.add_all([eng_a, eng_b])
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_a.id, user_id=admin_a.id, role=RoleName.admin)
    )
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )

    run_b = Run(
        engagement_id=eng_b.id,
        user_id=admin_b.id,
        tool="nmap",
        status=RunStatus.succeeded,
        organization_id=org_b.id,
    )
    db_session.add(run_b)
    await db_session.flush()

    finding_b = Finding(
        engagement_id=eng_b.id,
        reporter_id=admin_b.id,
        title="Secret vuln in B",
        description="Tenant B only",
        severity=FindingSeverity.critical,
        status=FindingStatus.new,
        fingerprint="tenant-b-secret-vuln",
        organization_id=org_b.id,
    )
    db_session.add(finding_b)
    await db_session.flush()

    evidence_b = Evidence(
        engagement_id=eng_b.id,
        run_id=run_b.id,
        type=EvidenceType.log,
        storage_key="evidence/org-b/secret.txt",
        metadata={"filename": "secret.txt"},
        organization_id=org_b.id,
    )
    db_session.add(evidence_b)
    await db_session.commit()

    token_a = create_access_token(admin_a.id, [RoleName.admin.value])
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Reports: cannot generate/access other tenant's engagement report
    r = await client.get(f"/api/reports/engagements/{eng_b.id}/generate", headers=headers_a)
    assert r.status_code in (403, 404)

    # Evidence: cannot list or download other tenant's evidence
    r = await client.get("/api/evidence", headers=headers_a)
    assert r.status_code == 200
    evidence_ids = [e["id"] for e in r.json()]
    assert str(evidence_b.id) not in evidence_ids

    r = await client.get(f"/api/evidence/{evidence_b.id}/download", headers=headers_a)
    assert r.status_code in (403, 404)

    # WS run status: existing inaccessible run must not leak existence
    r = await client.get(f"/api/ws/runs/{run_b.id}/status", headers=headers_a)
    assert r.status_code in (403, 404)

    # Direct run access across tenants must not leak existence
    r = await client.get(f"/api/runs/{run_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.get(f"/api/v1/runs/{run_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    # Persisted reports (engagement-scoped) must not leak across tenants
    from anomaly_core.models import Playbook, Report, ReportFormat, ReportStatus

    report_b = Report(
        organization_id=org_b.id,
        engagement_id=eng_b.id,
        version=1,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="# Report B\nsecret",
        author_id=admin_b.id,
    )
    db_session.add(report_b)
    await db_session.flush()

    r = await client.get(f"/api/reports/{report_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.get(f"/api/v1/reports/{report_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    # Playbooks (engagement-scoped) must not leak across tenants

    playbook_b = Playbook(engagement_id=eng_b.id, name="Secret Playbook B")
    db_session.add(playbook_b)
    await db_session.commit()
    await db_session.refresh(playbook_b)

    r = await client.get(f"/api/engagements/{eng_b.id}/playbooks", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.get(
        f"/api/engagements/{eng_b.id}/playbooks/{playbook_b.id}", headers=headers_a
    )
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_b.id}/playbooks/{playbook_b.id}/execute",
        headers=headers_a,
        json={"targets": ["in.scope.test"]},
    )
    assert r.status_code in (403, 404)
    r = await client.delete(
        f"/api/engagements/{eng_b.id}/playbooks/{playbook_b.id}", headers=headers_a
    )
    assert r.status_code in (403, 404)

    # Schedules (engagement-scoped) must not leak across tenants
    from anomaly_core.models import CronSchedule

    schedule_b = CronSchedule(
        engagement_id=eng_b.id,
        cron_expression="0 * * * *",
        tool="stub",
        targets=[],
        params={},
        is_active=True,
    )
    db_session.add(schedule_b)
    await db_session.commit()
    await db_session.refresh(schedule_b)

    r = await client.get(f"/api/engagements/{eng_b.id}/schedules", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.delete(
        f"/api/engagements/{eng_b.id}/schedules/{schedule_b.id}", headers=headers_a
    )
    assert r.status_code in (403, 404)

    # Aggregates/search must not include org B data
    r = await client.get("/api/vulnerabilities/summary", headers=headers_a)
    assert r.status_code == 200
    assert r.json()["critical"] == 0
    assert r.json()["total"] == 0

    r = await client.get("/api/search", params={"q": "Secret"}, headers=headers_a)
    assert r.status_code == 200
    payload = r.json()
    finding_titles = [f.get("title") for f in payload.get("findings", [])]
    assert "Secret vuln in B" not in finding_titles

    # Direct finding access across tenants must not leak existence
    r = await client.get(f"/api/findings/{finding_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.patch(
        f"/api/findings/{finding_b.id}",
        headers=headers_a,
        json={"title": "hijacked"},
    )
    assert r.status_code in (403, 404)
    r = await client.delete(f"/api/findings/{finding_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    r = await client.get("/api/stats", headers=headers_a)
    assert r.status_code == 200
    stats = r.json()
    assert stats["engagements"] == 1
    assert stats["findings"] == 0
    assert stats["runs"] == 0

    r = await client.get("/api/dashboard", headers=headers_a)
    assert r.status_code == 200
    data = r.json()
    overview = data["overview"]
    assert overview["engagements"] == 1
    assert overview["findings"] == 0
    assert overview["runs"] == 0
    assert data["severity"]["critical"] == 0
    assert data["severity"]["high"] == 0


@pytest.mark.asyncio
async def test_cross_tenant_audit_isolation(client, db_session):
    """Audit logs must not leak across tenant boundaries."""
    from anomaly_core.audit import AuditService

    admin_a = await _seed(db_session, "audit-admin-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "audit-admin-b@example.com", RoleName.admin)

    org_a = Organization(name="Audit Org A", slug="audit-org-a")
    org_b = Organization(name="Audit Org B", slug="audit-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_b = Engagement(
        name="Audit Eng B",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
    )
    db_session.add(eng_b)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )
    await db_session.flush()

    await AuditService.log(
        actor_id=admin_b.id,
        action="engagement.create",
        resource_type="engagement",
        resource_id=eng_b.id,
        engagement_id=eng_b.id,
        organization_id=org_b.id,
        metadata={"secret": "org-b-only"},
        db=db_session,
    )
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }

    r = await client.get(f"/api/audit?engagement_id={eng_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    r = await client.get("/api/audit", headers=headers_a)
    assert r.status_code == 200
    actions = [log.get("metadata", {}).get("secret") for log in r.json()]
    assert "org-b-only" not in actions
    engagement_ids = [log.get("engagement_id") for log in r.json()]
    assert str(eng_b.id) not in engagement_ids


@pytest.mark.asyncio
async def test_cross_tenant_user_listing_isolation(client, db_session):
    """Admin user listing must not expose users from other organizations."""
    admin_a = await _seed(db_session, "users-admin-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "users-admin-b@example.com", RoleName.admin)
    outsider_b = await _seed(db_session, "users-outsider-b@example.com", RoleName.pentester)

    org_a = Organization(name="Users Org A", slug="users-org-a")
    org_b = Organization(name="Users Org B", slug="users-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))
    db_session.add(Membership(user_id=outsider_b.id, organization_id=org_b.id, role="member"))
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }
    r = await client.get("/api/users", headers=headers_a)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert "users-admin-a@example.com" in emails
    assert "users-admin-b@example.com" not in emails
    assert "users-outsider-b@example.com" not in emails


@pytest.mark.asyncio
async def test_cross_tenant_v1_report_isolation(client, db_session):
    """V1 report generation must not leak cross-tenant engagement data."""
    admin_a = await _seed(db_session, "v1-report-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "v1-report-b@example.com", RoleName.admin)

    org_a = Organization(name="V1 Org A", slug="v1-org-a")
    org_b = Organization(name="V1 Org B", slug="v1-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_b = Engagement(
        name="V1 Eng B",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
    )
    db_session.add(eng_b)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }
    r = await client.get(f"/api/v1/engagements/{eng_b.id}/reports/generate", headers=headers_a)
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_tenant_playbook_isolation(client, db_session):
    """Playbooks must not be accessible or executable across tenant boundaries."""
    from anomaly_core.models import Playbook, PlaybookStep

    admin_a = await _seed(db_session, "pb-admin-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "pb-admin-b@example.com", RoleName.admin)

    org_a = Organization(name="PB Org A", slug="pb-org-a")
    org_b = Organization(name="PB Org B", slug="pb-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_a = Engagement(
        name="PB Eng A",
        mode=EngagementMode.own_infra,
        owner_id=admin_a.id,
        organization_id=org_a.id,
    )
    eng_b = Engagement(
        name="PB Eng B",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
    )
    db_session.add_all([eng_a, eng_b])
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_a.id, user_id=admin_a.id, role=RoleName.admin)
    )
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )
    await db_session.flush()

    pb_b = Playbook(engagement_id=eng_b.id, name="PB-B", description="secret")
    db_session.add(pb_b)
    await db_session.flush()
    db_session.add(PlaybookStep(playbook_id=pb_b.id, name="s1", tool="nmap", params={}, order=1))
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }

    # Cannot access playbook via other tenant's engagement path
    r = await client.get(f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}/execute",
        headers=headers_a,
        json={"targets": ["example.com"]},
    )
    assert r.status_code in (403, 404)
    r = await client.delete(f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)

    # Cannot confuse binding by using own engagement path with foreign playbook id
    r = await client.get(f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}/execute",
        headers=headers_a,
        json={"targets": ["example.com"]},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_tenant_v1_governed_actions_isolation(client, db_session):
    """V1 approve and run creation must not leak or allow cross-tenant access."""
    from anomaly_core.models import Scope, ScopeEntry, ScopeEntryKind

    admin_a = await _seed(db_session, "v1-gov-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "v1-gov-b@example.com", RoleName.admin)

    org_a = Organization(name="V1 Gov Org A", slug="v1-gov-org-a")
    org_b = Organization(name="V1 Gov Org B", slug="v1-gov-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_b = Engagement(
        name="V1 Gov Eng B",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
    )
    db_session.add(eng_b)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )
    scope_b = Scope(engagement_id=eng_b.id)
    db_session.add(scope_b)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope_b.id, kind=ScopeEntryKind.in_, target_value="in.scope.test")
    )
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }

    # Cross-tenant v1 approve must not leak existence.
    r = await client.post(f"/api/v1/engagements/{eng_b.id}/approve", headers=headers_a)
    assert r.status_code in (403, 404)

    # Cross-tenant v1 run creation must not leak existence or enqueue.
    r = await client.post(
        f"/api/v1/engagements/{eng_b.id}/runs",
        headers=headers_a,
        json={"tool": "stub", "targets": ["in.scope.test"], "params": {}},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_tenant_aggregate_endpoints_do_not_leak(client, db_session):
    """Aggregate/read endpoints must not include other tenants' data."""
    from anomaly_core.models import (
        AuditLog,
        EngagementStatus,
        Finding,
        FindingSeverity,
        FindingStatus,
        Run,
        RunStatus,
    )

    admin_a = await _seed(db_session, "agg-admin-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "agg-admin-b@example.com", RoleName.admin)

    org_a = Organization(name="Agg Org A", slug="agg-org-a")
    org_b = Organization(name="Agg Org B", slug="agg-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"))

    eng_a = Engagement(
        name="Agg Eng A",
        mode=EngagementMode.own_infra,
        owner_id=admin_a.id,
        organization_id=org_a.id,
        status=EngagementStatus.active,
    )
    eng_b = Engagement(
        name="Agg Eng B SECRET",
        mode=EngagementMode.own_infra,
        owner_id=admin_b.id,
        organization_id=org_b.id,
        status=EngagementStatus.active,
    )
    db_session.add_all([eng_a, eng_b])
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=eng_a.id, user_id=admin_a.id, role=RoleName.admin)
    )
    db_session.add(
        EngagementMember(engagement_id=eng_b.id, user_id=admin_b.id, role=RoleName.admin)
    )

    db_session.add(
        Finding(
            organization_id=org_b.id,
            engagement_id=eng_b.id,
            title="SECRET-FINDING-B",
            severity=FindingSeverity.critical,
            status=FindingStatus.new,
            description="",
            fingerprint="agg-fp-b",
            reporter_id=admin_b.id,
        )
    )
    db_session.add(
        Run(
            organization_id=org_b.id,
            engagement_id=eng_b.id,
            tool="nmap",
            status=RunStatus.succeeded,
            user_id=admin_b.id,
        )
    )
    db_session.add(
        AuditLog(
            organization_id=org_b.id,
            engagement_id=eng_b.id,
            action="engagement.create",
            resource_type="engagement",
            resource_id=eng_b.id,
            metadata={"name": "Agg Eng B SECRET"},
        )
    )
    await db_session.commit()

    headers_a = {
        "Authorization": f"Bearer {create_access_token(admin_a.id, [RoleName.admin.value])}"
    }

    # Dashboard/stats aggregates must not count other tenant data.
    for path in ("/api/dashboard", "/api/stats", "/api/vulnerabilities/summary"):
        r = await client.get(path, headers=headers_a)
        assert r.status_code == 200, path
        body = r.json()
        text = str(body)
        assert "SECRET" not in text
        if path == "/api/dashboard":
            assert body["overview"]["engagements"] == 1
            assert body["overview"]["findings"] == 0
            assert body["overview"]["runs"] == 0
        if path == "/api/stats":
            assert body == {"engagements": 1, "findings": 0, "runs": 0}
        if path == "/api/vulnerabilities/summary":
            assert body["total"] == 0
            assert body["critical"] == 0

    # Search must not return other tenant's engagements/findings.
    r = await client.get("/api/search?q=SECRET", headers=headers_a)
    assert r.status_code == 200
    body = r.json()
    assert body["engagements"] == []
    assert body["findings"] == []

    # Global audit list must not leak other tenant's audit logs.
    r = await client.get("/api/audit", headers=headers_a)
    assert r.status_code == 200
    actions = r.json()
    assert all(a.get("engagement_id") != str(eng_b.id) for a in actions)
    assert all("SECRET" not in str(a) for a in actions)
