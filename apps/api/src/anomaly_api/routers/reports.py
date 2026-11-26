from __future__ import annotations

import hashlib
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.models import (
    Engagement,
    Evidence,
    Finding,
    Report,
    ReportFormat,
    ReportStatus,
    RoleName,
    Run,
)
from anomaly_core.rbac import engagement_accessible
from anomaly_reporting import ReportGenerator
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession
from anomaly_api.report_integrity import recorded_report_sha256, report_verification
from anomaly_api.tenancy import child_organization_matches_engagement

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/engagements/{engagement_id}")
async def list_reports(engagement_id: UUID, user: CurrentUser, db: DbSession):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None or not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Engagement not found")
    rows = (
        await db.scalars(
            select(Report)
            .where(Report.engagement_id == engagement_id)
            .order_by(Report.version.desc(), Report.created_at.desc())
        )
    ).all()
    rows = [r for r in rows if child_organization_matches_engagement(r, engagement)]
    await AuditService.log(
        actor_id=user.id,
        action="report.list",
        resource_type="engagement",
        resource_id=engagement_id,
        engagement_id=engagement_id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"count": len(rows)},
        db=db,
    )
    await db.commit()
    return [
        {
            "id": str(r.id),
            "engagement_id": str(r.engagement_id),
            "version": r.version,
            "status": r.status.value,
            "format": r.format.value,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "sha256": hashlib.sha256(r.content.encode("utf-8")).hexdigest() if r.content else None,
        }
        for r in rows
    ]


@router.get("/{report_id}")
async def get_report(report_id: UUID, user: CurrentUser, db: DbSession):
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    engagement = await db.get(Engagement, report.engagement_id)
    if (
        engagement is None
        or not await engagement_accessible(db, user, engagement)
        or not child_organization_matches_engagement(report, engagement)
    ):
        raise HTTPException(status_code=404, detail="Report not found")
    await AuditService.log(
        actor_id=user.id,
        action="report.access",
        resource_type="report",
        resource_id=report.id,
        engagement_id=report.engagement_id,
        organization_id=getattr(report, "organization_id", None),
        metadata={"format": report.format.value, "version": report.version},
        db=db,
    )
    await db.commit()
    content_sha = (
        hashlib.sha256(report.content.encode("utf-8")).hexdigest() if report.content else None
    )
    recorded_sha = await recorded_report_sha256(db, report.id)
    verification = report_verification(content_sha, recorded_sha)
    return {
        "id": str(report.id),
        "engagement_id": str(report.engagement_id),
        "version": report.version,
        "status": report.status.value,
        "format": report.format.value,
        "content": report.content,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "traceability": {
            "organization_id": str(getattr(report, "organization_id", "") or ""),
            "engagement_id": str(report.engagement_id),
            "report_sha256": content_sha,
            "recorded_sha256": recorded_sha,
            "verification": verification,
            "verified": verification == "match",
        },
    }


@router.get("/engagements/{engagement_id}/generate")
async def generate_report(
    engagement_id: UUID,
    user: CurrentUser,
    db: DbSession,
    format: str = Query(default="markdown", pattern="^(markdown|html|pdf)$"),
) -> dict[str, object]:
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    # Hide existence from non-members/cross-tenant callers.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.client_viewer):
        raise HTTPException(status_code=404, detail="Engagement not found")
    # Report generation persists artifacts and is restricted to pentester+.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=403, detail="Forbidden")

    findings = (
        await db.scalars(select(Finding).where(Finding.engagement_id == engagement_id))
    ).all()
    runs = (await db.scalars(select(Run).where(Run.engagement_id == engagement_id))).all()
    evidence_rows = (
        await db.scalars(select(Evidence).where(Evidence.engagement_id == engagement_id))
    ).all()
    if not evidence_rows and runs:
        run_ids = [r.id for r in runs]
        evidence_rows = (
            (await db.scalars(select(Evidence).where(Evidence.run_id.in_(run_ids)))).all()
            if run_ids
            else []
        )

    findings_data = [
        {
            "title": f.title,
            "severity": f.severity.value,
            "description": f.description,
            "status": f.status.value,
            "remediation": f.remediation or "",
        }
        for f in findings
    ]
    run_ids_str = [str(r.id) for r in runs]
    ev_ids = [str(e.id) for e in evidence_rows]
    ev_shas = [e.sha256 or (e.metadata or {}).get("sha256") for e in evidence_rows]
    ev_shas = [s for s in ev_shas if s]
    context = {
        "organization_id": str(getattr(engagement, "organization_id", "") or ""),
        "engagement_id": str(engagement_id),
        "job_id": run_ids_str[0] if run_ids_str else None,
        "run_id": run_ids_str[0] if run_ids_str else None,
        "execution_id": run_ids_str[0] if run_ids_str else None,
        "evidence_ids": ev_ids,
        "evidence_sha256": ev_shas,
    }

    gen = ReportGenerator()
    content: str | bytes
    if format == "html":
        content = gen.generate_html(engagement.name, findings_data, context=context)
    elif format == "pdf":
        content = gen.generate_pdf(engagement.name, findings_data, context=context)
    else:
        content = gen.generate_markdown(engagement.name, findings_data, context=context)

    content_str = content.decode("utf-8") if isinstance(content, bytes) else content
    report_sha = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
    context = {**context, "report_sha256": report_sha}

    fmt = (
        ReportFormat(format)
        if format in ReportFormat._value2member_map_
        else ReportFormat.markdown
    )
    max_version = await db.scalar(
        select(func.max(Report.version)).where(Report.engagement_id == engagement_id)
    )
    next_version = int(max_version or 0) + 1
    report = Report(
        organization_id=getattr(engagement, "organization_id", None),
        engagement_id=engagement_id,
        version=next_version,
        status=ReportStatus.draft,
        format=fmt,
        content=content_str,
        author_id=user.id,
    )
    db.add(report)
    await db.flush()
    await AuditService.log(
        actor_id=user.id,
        action="report.generate",
        resource_type="report",
        resource_id=report.id,
        engagement_id=engagement_id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"format": format, "report_sha256": report_sha, "version": next_version},
        db=db,
    )
    await db.commit()
    await db.refresh(report)

    return {
        "report_id": str(report.id),
        "engagement_id": str(engagement_id),
        "engagement_name": engagement.name,
        "format": format,
        "content": content_str,
        "finding_count": len(findings_data),
        "traceability": context,
    }
