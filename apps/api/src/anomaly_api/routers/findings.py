from __future__ import annotations

from typing import Annotated
from uuid import UUID

from anomaly_core.models import Engagement, Finding, FindingSeverity, FindingStatus, RoleName
from anomaly_core.rbac import engagement_accessible, has_role
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(tags=["findings"])


@router.get("/api/engagements/{engagement_id}/findings")
async def list_findings(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    db: DbSession,
):
    findings = (await db.scalars(select(Finding).where(Finding.engagement_id == engagement.id))).all()
    return [
        {
            "id": str(f.id),
            "title": f.title,
            "severity": f.severity.value,
            "status": f.status.value,
        }
        for f in findings
    ]


@router.post("/api/engagements/{engagement_id}/findings", status_code=status.HTTP_201_CREATED)
async def create_finding(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    payload: dict,
    db: DbSession,
    user: CurrentUser,
):
    if has_role(user, RoleName.client_viewer) and not has_role(user, RoleName.pentester) and not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Also check - client_viewer members shouldn't be able to create
    from anomaly_core.rbac import get_membership

    membership = await get_membership(db, user, engagement)
    if membership is not None and membership.role == RoleName.client_viewer and not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    finding = Finding(
        engagement_id=engagement.id,
        title=payload.get("title", ""),
        severity=FindingSeverity(payload.get("severity", "info")),
        description=payload.get("description", ""),
        reporter_id=user.id,
        fingerprint=f"{engagement.id}:{payload.get('title','')}",
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return {"id": str(finding.id), "title": finding.title}


@router.get("/api/findings/{finding_id}")
async def get_finding(finding_id: UUID, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Finding not found")
    return {
        "id": str(finding.id),
        "engagement_id": str(finding.engagement_id),
        "title": finding.title,
        "severity": finding.severity.value,
    }
