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
async def test_child_rows_with_foreign_org_are_hidden_from_accessible_engagement(
    client, db_session
):
    """Defense in depth: child org must agree with the accessible engagement's org."""
    from anomaly_core.models import (
        Evidence as EvidenceModel,
    )
    from anomaly_core.models import (
        EvidenceType,
        Report,
        ReportFormat,
        ReportStatus,
    )

    admin = await _seed(db_session, "child-org-a@example.com", RoleName.admin)
    other = await _seed(db_session, "child-org-b@example.com", RoleName.admin)
    org_a = Organization(name="Child Org A", slug="child-org-a")
    org_b = Organization(name="Child Org B", slug="child-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=other.id, organization_id=org_b.id, role="owner"))

    engagement = Engagement(
        name="Child Org Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org_a.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )

    consistent_report = Report(
        organization_id=org_a.id,
        engagement_id=engagement.id,
        version=1,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="# Consistent",
        author_id=admin.id,
    )
    mismatched_report = Report(
        organization_id=org_b.id,
        engagement_id=engagement.id,
        version=2,
        status=ReportStatus.draft,
        format=ReportFormat.markdown,
        content="# Foreign SECRET",
        author_id=admin.id,
    )
    consistent_evidence = EvidenceModel(
        organization_id=org_a.id,
        engagement_id=engagement.id,
        type=EvidenceType.log,
        storage_key="logs/consistent.txt",
        sha256="d" * 64,
        collector="worker",
        tool="nmap",
        metadata={"stdout": "consistent"},
    )
    mismatched_evidence = EvidenceModel(
        organization_id=org_b.id,
        engagement_id=engagement.id,
        type=EvidenceType.log,
        storage_key="logs/foreign.txt",
        sha256="e" * 64,
        collector="worker",
        tool="nmap",
        metadata={"stdout": "foreign secret"},
    )
    db_session.add_all(
        [consistent_report, mismatched_report, consistent_evidence, mismatched_evidence]
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, [RoleName.admin.value])}"}

    # Direct reads must hide mismatched children but keep consistent ones readable.
    for path in (
        f"/api/reports/{mismatched_report.id}",
        f"/api/v1/reports/{mismatched_report.id}",
        f"/api/evidence/{mismatched_evidence.id}/download",
        f"/api/evidence/{mismatched_evidence.id}/file",
        f"/api/evidence/{mismatched_evidence.id}/integrity",
    ):
        r = await client.get(path, headers=headers)
        assert r.status_code == 404, path

    r = await client.get(f"/api/reports/{consistent_report.id}", headers=headers)
    assert r.status_code == 200
    r = await client.get(f"/api/evidence/{consistent_evidence.id}/download", headers=headers)
    assert r.status_code == 200

    # Collection reads must not enumerate mismatched children.
    for path in (
        f"/api/reports/engagements/{engagement.id}",
        f"/api/v1/engagements/{engagement.id}/reports",
    ):
        r = await client.get(path, headers=headers)
        assert r.status_code == 200
        payload = r.json()
        rows = payload if isinstance(payload, list) else payload["data"]
        ids = [row["id"] for row in rows]
        assert str(consistent_report.id) in ids
        assert str(mismatched_report.id) not in ids

    r = await client.get("/api/evidence", headers=headers)
    assert r.status_code == 200
    evidence_ids = [row["id"] for row in r.json()]
    assert str(consistent_evidence.id) in evidence_ids
    assert str(mismatched_evidence.id) not in evidence_ids


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

    # Reports: cannot generate/list/access other tenant's engagement report
    r = await client.get(f"/api/reports/engagements/{eng_b.id}/generate", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.get(f"/api/reports/engagements/{eng_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/v1/engagements/{eng_b.id}/reports",
        headers=headers_a,
        json={"format": "markdown"},
    )
    assert r.status_code in (403, 404)
    r = await client.get(f"/api/v1/engagements/{eng_b.id}/reports", headers=headers_a)
    assert r.status_code in (403, 404)

    # Evidence: cannot list or download/access other tenant's evidence
    r = await client.get("/api/evidence", headers=headers_a)
    assert r.status_code == 200
    evidence_ids = [e["id"] for e in r.json()]
    assert str(evidence_b.id) not in evidence_ids

    for path in (
        f"/api/evidence/{evidence_b.id}/download",
        f"/api/evidence/{evidence_b.id}/file",
        f"/api/evidence/{evidence_b.id}/integrity",
    ):
        r = await client.get(path, headers=headers_a)
        assert r.status_code in (403, 404), path

    # WS run status: existing inaccessible run must not leak existence
    r = await client.get(f"/api/ws/runs/{run_b.id}/status", headers=headers_a)
    assert r.status_code == 404

    # Direct run access across tenants must not leak existence
    r = await client.get(f"/api/runs/{run_b.id}", headers=headers_a)
    assert r.status_code == 404
    r = await client.get(f"/api/v1/runs/{run_b.id}", headers=headers_a)
    assert r.status_code == 404

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
    assert r.status_code == 404
    r = await client.get(f"/api/v1/reports/{report_b.id}", headers=headers_a)
    assert r.status_code == 404

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
    r = await client.post(
        f"/api/engagements/{eng_b.id}/playbooks",
        headers=headers_a,
        json={"name": "x", "description": "x", "steps": []},
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
    r = await client.post(
        f"/api/engagements/{eng_b.id}/schedules",
        headers=headers_a,
        json={
            "cron_expression": "0 * * * *",
            "tool": "nmap",
            "targets": ["10.0.0.1"],
            "params": {},
        },
    )
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

    # Engagement-scoped finding/run list/create must not leak across tenants
    r = await client.get(f"/api/engagements/{eng_b.id}/findings", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_b.id}/findings",
        headers=headers_a,
        json={"title": "x", "severity": "low", "description": "x"},
    )
    assert r.status_code in (403, 404)
    r = await client.get(f"/api/engagements/{eng_b.id}/runs", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_b.id}/runs",
        headers=headers_a,
        json={"tool": "stub", "targets": ["in.scope.test"], "params": {}},
    )
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
    r = await client.patch(
        f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}",
        headers=headers_a,
        json={"name": "hijacked"},
    )
    assert r.status_code in (403, 404)
    r = await client.delete(f"/api/engagements/{eng_b.id}/playbooks/{pb_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.post(
        f"/api/engagements/{eng_b.id}/playbooks",
        headers=headers_a,
        json={"name": "x", "description": "x", "steps": []},
    )
    assert r.status_code in (403, 404)

    # Cannot confuse binding by using own engagement path with foreign playbook id
    r = await client.get(f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}", headers=headers_a)
    assert r.status_code in (403, 404)
    r = await client.patch(
        f"/api/engagements/{eng_a.id}/playbooks/{pb_b.id}",
        headers=headers_a,
        json={"name": "hijacked"},
    )
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
    db_session.add(
        AuditLog(
            organization_id=None,
            action="system.secret",
            resource_type="system",
            resource_id=eng_b.id,
            actor_id=admin_b.id,
            metadata={"secret": "NULL-ORG-B"},
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
    assert all("NULL-ORG-B" not in str(a) for a in actions)
    assert all(a.get("action") != "system.secret" for a in actions)


@pytest.mark.asyncio
async def test_finding_and_run_org_mismatch_is_hidden_everywhere(client, db_session):
    """Child org consistency must hold for findings/runs and their aggregates."""
    from anomaly_core.models import (
        Finding,
        FindingSeverity,
        FindingStatus,
        Run,
        RunStatus,
    )

    admin = await _seed(db_session, "fr-org-a@example.com", RoleName.admin)
    other = await _seed(db_session, "fr-org-b@example.com", RoleName.admin)
    org_a = Organization(name="Finding Run Org A", slug="finding-run-org-a")
    org_b = Organization(name="Finding Run Org B", slug="finding-run-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=other.id, organization_id=org_b.id, role="owner"))

    engagement = Engagement(
        name="Finding Run Org Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org_a.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )

    consistent_finding = Finding(
        organization_id=org_a.id,
        engagement_id=engagement.id,
        title="ConsistentRunFinding",
        severity=FindingSeverity.medium,
        status=FindingStatus.new,
        description="consistent",
        reporter_id=admin.id,
        fingerprint="fr-consistent",
    )
    mismatched_finding = Finding(
        organization_id=org_b.id,
        engagement_id=engagement.id,
        title="ForeignRunFinding",
        severity=FindingSeverity.medium,
        status=FindingStatus.new,
        description="foreign secret",
        reporter_id=admin.id,
        fingerprint="fr-foreign",
    )
    consistent_run = Run(
        organization_id=org_a.id,
        engagement_id=engagement.id,
        user_id=admin.id,
        tool="nmap",
        status=RunStatus.succeeded,
        target_ids=[],
        params={},
    )
    mismatched_run = Run(
        organization_id=org_b.id,
        engagement_id=engagement.id,
        user_id=admin.id,
        tool="nmap",
        status=RunStatus.succeeded,
        target_ids=[],
        params={},
    )
    db_session.add_all(
        [consistent_finding, mismatched_finding, consistent_run, mismatched_run]
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, [RoleName.admin.value])}"}

    for path in (
        f"/api/findings/{mismatched_finding.id}",
        f"/api/runs/{mismatched_run.id}",
        f"/api/v1/runs/{mismatched_run.id}",
        f"/api/ws/runs/{mismatched_run.id}/status",
    ):
        r = await client.get(path, headers=headers)
        assert r.status_code == 404, path

    r = await client.patch(
        f"/api/findings/{mismatched_finding.id}",
        headers=headers,
        json={"title": "Tampered"},
    )
    assert r.status_code == 404

    r = await client.get(f"/api/engagements/{engagement.id}/findings", headers=headers)
    assert r.status_code == 200
    assert [f["id"] for f in r.json()] == [str(consistent_finding.id)]

    r = await client.get(f"/api/engagements/{engagement.id}/runs", headers=headers)
    assert r.status_code == 200
    assert [run["id"] for run in r.json()] == [str(consistent_run.id)]

    r = await client.get("/api/search?q=RunFinding", headers=headers)
    assert r.status_code == 200
    finding_ids = [f["id"] for f in r.json()["findings"]]
    assert str(consistent_finding.id) in finding_ids
    assert str(mismatched_finding.id) not in finding_ids

    for path in ("/api/stats", "/api/dashboard"):
        r = await client.get(path, headers=headers)
        assert r.status_code == 200
        overview = r.json().get("overview", r.json())
        assert overview["findings"] == 1
        assert overview["runs"] == 1

    r = await client.get("/api/vulnerabilities/summary", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    for path, method in (
        (f"/api/reports/engagements/{engagement.id}/generate?format=markdown", "GET"),
        (f"/api/v1/engagements/{engagement.id}/reports/generate?format=markdown", "GET"),
    ):
        r = (
            await client.get(path, headers=headers)
            if method == "GET"
            else await client.post(path, headers=headers)
        )
        assert r.status_code == 200, path
        content = r.json().get("content") or r.json().get("data", {}).get("content", "")
        assert "ConsistentRunFinding" in content
        assert "ForeignRunFinding" not in content


@pytest.mark.asyncio
async def test_engagement_create_validates_requested_organization(client, db_session):
    single = await _seed(db_session, "create-org-single@example.com", RoleName.admin)
    multi = await _seed(db_session, "create-org-multi@example.com", RoleName.admin)
    owner_b = await _seed(db_session, "create-org-owner-b@example.com", RoleName.admin)
    org_a = Organization(name="Create Org A", slug="create-org-a")
    org_b = Organization(name="Create Org B", slug="create-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=single.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=multi.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=multi.id, organization_id=org_b.id, role="member"))
    db_session.add(Membership(user_id=owner_b.id, organization_id=org_b.id, role="owner"))
    await db_session.commit()

    headers_single = {
        "Authorization": f"Bearer {create_access_token(single.id, [RoleName.admin.value])}"
    }
    headers_multi = {
        "Authorization": f"Bearer {create_access_token(multi.id, [RoleName.admin.value])}"
    }

    for path in ("/api/engagements", "/api/v1/engagements"):
        r = await client.post(
            path,
            headers=headers_single,
            json={
                "name": "Foreign Create",
                "mode": "own_infra",
                "organization_id": str(org_b.id),
            },
        )
        assert r.status_code == 403, path

    count = await db_session.scalar(
        select(__import__("sqlalchemy").func.count(Engagement.id)).where(
            Engagement.name == "Foreign Create"
        )
    )
    assert count == 0

    r = await client.post(
        "/api/engagements",
        headers=headers_multi,
        json={
            "name": "Chosen Create",
            "mode": "own_infra",
            "organization_id": str(org_b.id),
        },
    )
    assert r.status_code == 201
    assert r.json()["organization_id"] == str(org_b.id)

    r = await client.post(
        "/api/v1/engagements",
        headers=headers_multi,
        json={
            "name": "Chosen V1 Create",
            "mode": "own_infra",
            "organization_id": str(org_b.id),
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["organization_id"] == str(org_b.id)


@pytest.mark.asyncio
async def test_tags_are_org_scoped(client, db_session):
    admin_a = await _seed(db_session, "tag-a@example.com", RoleName.admin)
    admin_b = await _seed(db_session, "tag-b@example.com", RoleName.admin)
    org_a = Organization(name="Tag Org A", slug="tag-org-a")
    org_b = Organization(name="Tag Org B", slug="tag-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add_all(
        [
            Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"),
            Membership(user_id=admin_b.id, organization_id=org_b.id, role="owner"),
        ]
    )
    await db_session.commit()

    headers_a = {"Authorization": f"Bearer {create_access_token(admin_a.id, ['admin'])}"}
    headers_b = {"Authorization": f"Bearer {create_access_token(admin_b.id, ['admin'])}"}

    r = await client.post(
        "/api/tags", headers=headers_a, json={"name": "internal", "color": "#111"}
    )
    assert r.status_code == 200
    tag_a = r.json()
    assert tag_a["organization_id"] == str(org_a.id)

    r = await client.get("/api/tags", headers=headers_a)
    assert r.status_code == 200
    assert any(t["name"] == "internal" for t in r.json())

    r = await client.get("/api/tags", headers=headers_b)
    assert r.status_code == 200
    assert all(t["name"] != "internal" for t in r.json())

    r = await client.post(
        "/api/tags",
        headers=headers_b,
        json={"name": "steal", "color": "#222", "organization_id": str(org_a.id)},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_governed_approval_persists_request_and_decision(client, db_session):
    from anomaly_core.models import Approval, ApprovalStatus

    admin = await _seed(db_session, "approval-trace-admin@example.com", RoleName.admin)
    org = Organization(name="Approval Trace Org", slug="approval-trace-org")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org.id, role="owner"))
    engagement = Engagement(
        name="Approval Trace Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, [RoleName.admin.value])}"}
    submitted = await client.post(f"/api/engagements/{engagement.id}/submit", headers=headers)
    assert submitted.status_code == 200

    approval = await db_session.scalar(
        select(Approval).where(Approval.engagement_id == engagement.id)
    )
    assert approval is not None
    assert approval.status == ApprovalStatus.pending
    assert approval.requester_id == admin.id
    assert approval.organization_id == org.id

    approved = await client.post(f"/api/engagements/{engagement.id}/approve", headers=headers)
    assert approved.status_code == 200

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.approved
    assert approval.approver_id == admin.id
    assert approval.decided_at is not None
    assert approval.resource_type == "engagement"
    assert approval.resource_id == engagement.id


@pytest.mark.asyncio
async def test_v1_approve_persists_approval_decision(client, db_session):
    from anomaly_core.models import Approval, ApprovalStatus

    admin = await _seed(db_session, "v1-approval-trace-admin@example.com", RoleName.admin)
    org = Organization(name="V1 Approval Trace Org", slug="v1-approval-trace-org")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org.id, role="owner"))
    engagement = Engagement(
        name="V1 Approval Trace Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, [RoleName.admin.value])}"}
    approved = await client.post(
        f"/api/v1/engagements/{engagement.id}/approve", headers=headers
    )
    assert approved.status_code == 200

    approval = await db_session.scalar(
        select(Approval).where(Approval.engagement_id == engagement.id)
    )
    assert approval is not None
    assert approval.status == ApprovalStatus.approved
    assert approval.organization_id == org.id
    assert approval.approver_id == admin.id
    assert approval.decided_at is not None


@pytest.mark.asyncio
async def test_approval_read_filters_foreign_org_rows(client, db_session):
    from anomaly_core.models import Approval, ApprovalStatus

    admin = await _seed(db_session, "approval-read-admin@example.com", RoleName.admin)
    other = await _seed(db_session, "approval-read-other@example.com", RoleName.admin)
    org_a = Organization(name="Approval Read Org A", slug="approval-read-org-a")
    org_b = Organization(name="Approval Read Org B", slug="approval-read-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=other.id, organization_id=org_b.id, role="owner"))
    engagement = Engagement(
        name="Approval Read Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org_a.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )
    consistent = Approval(
        organization_id=org_a.id,
        engagement_id=engagement.id,
        resource_type="engagement",
        resource_id=engagement.id,
        requester_id=admin.id,
        approver_id=admin.id,
        status=ApprovalStatus.approved,
    )
    mismatched = Approval(
        organization_id=org_b.id,
        engagement_id=engagement.id,
        resource_type="engagement",
        resource_id=engagement.id,
        requester_id=admin.id,
        approver_id=admin.id,
        status=ApprovalStatus.approved,
    )
    db_session.add_all([consistent, mismatched])
    await db_session.commit()

    headers = {"Authorization": f"Bearer {create_access_token(admin.id, [RoleName.admin.value])}"}
    legacy = await client.get(f"/api/engagements/{engagement.id}/approvals", headers=headers)
    assert legacy.status_code == 200
    legacy_ids = [row["id"] for row in legacy.json()]
    assert str(consistent.id) in legacy_ids
    assert str(mismatched.id) not in legacy_ids

    v1 = await client.get(f"/api/v1/engagements/{engagement.id}/approvals", headers=headers)
    assert v1.status_code == 200
    v1_ids = [row["id"] for row in v1.json()["data"]]
    assert str(consistent.id) in v1_ids
    assert str(mismatched.id) not in v1_ids


@pytest.mark.asyncio
async def test_approval_read_no_leak_for_cross_tenant_and_viewer(client, db_session):
    from anomaly_core.models import Approval, ApprovalStatus

    admin = await _seed(db_session, "approval-leak-admin@example.com", RoleName.admin)
    other = await _seed(db_session, "approval-leak-other@example.com", RoleName.admin)
    viewer = await _seed(db_session, "approval-leak-viewer@example.com", RoleName.client_viewer)
    org_a = Organization(name="Approval Leak Org A", slug="approval-leak-org-a")
    org_b = Organization(name="Approval Leak Org B", slug="approval-leak-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=other.id, organization_id=org_b.id, role="owner"))
    db_session.add(Membership(user_id=viewer.id, organization_id=org_a.id, role="member"))
    engagement = Engagement(
        name="Approval Leak Engagement",
        mode=EngagementMode.own_infra,
        owner_id=admin.id,
        organization_id=org_a.id,
    )
    db_session.add(engagement)
    await db_session.flush()
    db_session.add(
        EngagementMember(engagement_id=engagement.id, user_id=admin.id, role=RoleName.admin)
    )
    db_session.add(
        EngagementMember(
            engagement_id=engagement.id, user_id=viewer.id, role=RoleName.client_viewer
        )
    )
    db_session.add(
        Approval(
            organization_id=org_a.id,
            engagement_id=engagement.id,
            resource_type="engagement",
            resource_id=engagement.id,
            requester_id=admin.id,
            approver_id=admin.id,
            status=ApprovalStatus.approved,
        )
    )
    await db_session.commit()

    headers_admin = {"Authorization": f"Bearer {create_access_token(admin.id, ['admin'])}"}
    headers_other = {"Authorization": f"Bearer {create_access_token(other.id, ['admin'])}"}
    headers_viewer = {
        "Authorization": f"Bearer {create_access_token(viewer.id, ['client_viewer'])}"
    }

    for path in (
        f"/api/engagements/{engagement.id}/approvals",
        f"/api/v1/engagements/{engagement.id}/approvals",
    ):
        cross_tenant = await client.get(path, headers=headers_other)
        assert cross_tenant.status_code == 404, path
        viewer_read = await client.get(path, headers=headers_viewer)
        assert viewer_read.status_code == 403, path
        allowed = await client.get(path, headers=headers_admin)
        assert allowed.status_code == 200, path
