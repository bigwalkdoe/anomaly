from __future__ import annotations

from uuid import UUID

from anomaly_core.models import Engagement, Finding
from anomaly_reporting import ReportGenerator
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/engagements/{engagement_id}/generate")
async def generate_report(
    engagement_id: UUID,
    format: str = Query(default="markdown", pattern="^(markdown|html|pdf)$"),
    user: CurrentUser = None,
    db: DbSession = None,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings = (
        await db.scalars(select(Finding).where(Finding.engagement_id == engagement_id))
    ).all()

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

    gen = ReportGenerator()
    if format == "html":
        content = gen.generate_html(engagement.name, findings_data)
    elif format == "pdf":
        content = gen.generate_pdf(engagement.name, findings_data)
    else:
        content = gen.generate_markdown(engagement.name, findings_data)

    return {
        "engagement_id": str(engagement_id),
        "engagement_name": engagement.name,
        "format": format,
        "content": content.decode("utf-8") if isinstance(content, bytes) else content,
        "finding_count": len(findings_data),
    }
