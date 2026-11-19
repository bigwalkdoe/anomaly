from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, Finding, FindingSeverity, FindingStatus, RoleName
from anomaly_core.rbac import engagement_accessible, get_membership, has_role
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)


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
        organization_id=getattr(engagement, "organization_id", None),
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
        organization_id=getattr(engagement, "organization_id", None),
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
    # Hide existence from non-members/cross-tenant callers.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.client_viewer):
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse.model_validate(finding)


async def _require_finding_mutation_access(
    db: DbSession, user: CurrentUser, finding_id: UUID
) -> tuple[Finding, Engagement]:
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    engagement = await db.get(Engagement, finding.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    # Hide existence from non-members/cross-tenant callers.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.client_viewer):
        raise HTTPException(status_code=404, detail="Finding not found")
    # Known/accessible finding but insufficient role for mutation.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=403, detail="Forbidden")
    return finding, engagement


@router.patch("/api/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: UUID, payload: FindingUpdate, user: CurrentUser, db: DbSession
):
    finding, engagement = await _require_finding_mutation_access(db, user, finding_id)
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
        organization_id=getattr(engagement, "organization_id", None),
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
    finding, engagement = await _require_finding_mutation_access(db, user, finding_id)
    finding.status = FindingStatus(payload.status)
    await AuditService.log(
        actor_id=user.id,
        action="finding.status_transition",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"status": finding.status.value},
        db=db,
    )
    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)


@router.delete("/api/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finding(finding_id: UUID, user: CurrentUser, db: DbSession):
    finding, engagement = await _require_finding_mutation_access(db, user, finding_id)
    await AuditService.log(
        actor_id=user.id,
        action="finding.delete",
        resource_type="finding",
        resource_id=finding.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={},
        db=db,
    )
    await db.delete(finding)
    await db.commit()
    return None
