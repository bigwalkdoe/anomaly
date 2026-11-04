from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, Finding, FindingSeverity, FindingStatus, RoleName
from anomaly_core.rbac import engagement_accessible, get_membership, has_role
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
    membership = await get_membership(db, user, engagement)
    if membership is not None and membership.role == RoleName.client_viewer and not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    if has_role(user, RoleName.client_viewer) and not has_role(user, RoleName.admin):
        # extra check
        raise HTTPException(status_code=403, detail="Forbidden")
    finding = Finding(
        engagement_id=engagement.id,
        title=payload.get("title", ""),
        severity=FindingSeverity(payload.get("severity", "info")),
        description=payload.get("description", ""),
        reporter_id=user.id,
        fingerprint=f"{engagement.id}:{payload.get('title','')}:{uuid4()}",
    )
    db.add(finding)
    await AuditService.log(
        actor_id=user.id,
        action="finding.create",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        metadata={"title": finding.title},
        db=db,
    )
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
        "status": finding.status.value,
        "description": finding.description,
    }


@router.patch("/api/findings/{finding_id}")
async def update_finding(finding_id: UUID, payload: dict, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=404, detail="Finding not found")
    if "status" in payload:
        finding.status = FindingStatus(payload["status"])
    if "title" in payload:
        finding.title = payload["title"]
    if "severity" in payload:
        finding.severity = FindingSeverity(payload["severity"])
    if "description" in payload:
        finding.description = payload["description"]
    await AuditService.log(
        actor_id=user.id,
        action="finding.update",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        metadata=payload,
        db=db,
    )
    await db.commit()
    await db.refresh(finding)
    return {"id": str(finding.id), "status": finding.status.value}


@router.post("/api/findings/{finding_id}/status")
async def transition_finding_status(finding_id: UUID, payload: dict, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=404, detail="Finding not found")
    if "status" in payload:
        finding.status = FindingStatus(payload["status"])
    await AuditService.log(
        actor_id=user.id,
        action="finding.status_transition",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        metadata={"status": finding.status.value},
        db=db,
    )
    await db.commit()
    await db.refresh(finding)
    return {"id": str(finding.id), "status": finding.status.value}


@router.delete("/api/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finding(finding_id: UUID, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=404, detail="Finding not found")
    await AuditService.log(
        actor_id=user.id,
        action="finding.delete",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        metadata={},
        db=db,
    )
    await db.delete(finding)
    await db.commit()
    return None


@router.post("/api/engagements/{engagement_id}/findings/bulk")
async def bulk_create_findings(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    payload: dict,
    db: DbSession,
    user: CurrentUser,
):
    findings = []
    for item in payload.get("findings", []):
        finding = Finding(
            engagement_id=engagement.id,
            title=item.get("title", ""),
            severity=FindingSeverity(item.get("severity", "info")),
            description=item.get("description", ""),
            reporter_id=user.id,
            fingerprint=f"{engagement.id}:{item.get('title')}:{uuid4()}",
        )
        db.add(finding)
        findings.append(finding)
    await db.commit()
    return {"created": len(findings)}
