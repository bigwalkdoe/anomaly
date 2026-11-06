from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, Finding, FindingSeverity, FindingStatus, RoleName
from anomaly_core.rbac import engagement_accessible, get_membership, has_role
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access
from anomaly_api.schemas.engagement import TargetResponse  # noqa: F401

router = APIRouter(tags=["findings"])


class FindingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    severity: str = Field(default="info")
    description: str = Field(default="")


class FindingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    severity: str | None = None
    status: str | None = None
    description: str | None = None
    remediation: str | None = None


class FindingResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    title: str
    severity: str
    status: str
    description: str

    class Config:
        from_attributes = True


class FindingStatusTransition(BaseModel):
    status: str


@router.get("/api/engagements/{engagement_id}/findings", response_model=list[FindingResponse])
async def list_findings(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    db: DbSession,
):
    findings = (
        await db.scalars(select(Finding).where(Finding.engagement_id == engagement.id))
    ).all()
    return [FindingResponse.model_validate(f) for f in findings]


@router.post(
    "/api/engagements/{engagement_id}/findings",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_finding(
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    payload: FindingCreate,
    db: DbSession,
    user: CurrentUser,
):
    membership = await get_membership(db, user, engagement)
    if (
        membership is not None
        and membership.role == RoleName.client_viewer
        and not has_role(user, RoleName.admin)
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    if has_role(user, RoleName.client_viewer) and not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    finding = Finding(
        engagement_id=engagement.id,
        title=payload.title,
        severity=FindingSeverity(payload.severity),
        description=payload.description,
        reporter_id=user.id,
        fingerprint=f"{engagement.id}:{payload.title}:{uuid4()}",
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
    return FindingResponse.model_validate(finding)


@router.get("/api/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: UUID, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse.model_validate(finding)


@router.patch("/api/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: UUID, payload: FindingUpdate, user: CurrentUser, db: DbSession
):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(
        db, user, engagement, min_role=RoleName.pentester
    ):
        raise HTTPException(status_code=404, detail="Finding not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data:
        finding.status = FindingStatus(update_data["status"])
    if "title" in update_data:
        finding.title = update_data["title"]
    if "severity" in update_data:
        finding.severity = FindingSeverity(update_data["severity"])
    if "description" in update_data:
        finding.description = update_data["description"]
    if "remediation" in update_data:
        finding.remediation = update_data["remediation"]
    await AuditService.log(
        actor_id=user.id,
        action="finding.update",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        metadata=update_data,
        db=db,
    )
    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)


@router.post("/api/findings/{finding_id}/status", response_model=FindingResponse)
async def transition_finding_status(
    finding_id: UUID, payload: FindingStatusTransition, user: CurrentUser, db: DbSession
):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(
        db, user, engagement, min_role=RoleName.pentester
    ):
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.status = FindingStatus(payload.status)
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
    return FindingResponse.model_validate(finding)


@router.delete("/api/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finding(finding_id: UUID, user: CurrentUser, db: DbSession):
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None or not await engagement_accessible(
        db, user, engagement, min_role=RoleName.pentester
    ):
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
