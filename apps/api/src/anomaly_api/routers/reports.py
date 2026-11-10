from __future__ import annotations

from uuid import UUID

from anomaly_core.models import Engagement, Evidence, Finding, Run
from anomaly_reporting import ReportGenerator
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/reports", tags=["reports"])


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

    findings = (
        await db.scalars(select(Finding).where(Finding.engagement_id == engagement_id))
    ).all()
    runs = (await db.scalars(select(Run).where(Run.engagement_id == engagement_id))).all()
    evidence_rows = (await db.scalars(select(Evidence).where(Evidence.engagement_id == engagement_id))).all()
    if not evidence_rows and runs:
        run_ids = [r.id for r in runs]
        evidence_rows = (await db.scalars(select(Evidence).where(Evidence.run_id.in_(run_ids)))).all() if run_ids else []

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

    return {
        "engagement_id": str(engagement_id),
        "engagement_name": engagement.name,
        "format": format,
        "content": content.decode("utf-8") if isinstance(content, bytes) else content,
        "finding_count": len(findings_data),
        "traceability": context,
    }
