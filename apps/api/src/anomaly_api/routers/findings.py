from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db
from anomaly_api.schemas.finding import FindingOut, FindingStatusUpdate, FindingUpdate
from anomaly_core.audit import AuditService
from anomaly_core.models.finding import Finding, FindingSeverity, FindingStatus
from anomaly_core.models.user import User
from anomaly_core.rbac import can_access_engagement

router = APIRouter(prefix="/api/findings", tags=["findings"])


def _out(f: Finding) -> FindingOut:
    return FindingOut(
        id=str(f.id),
        engagement_id=str(f.engagement_id),
        title=f.title,
        severity=f.severity.value,
        status=f.status.value,
        description=f.description,
    )


async def _get_accessible_finding(
    finding_id: UUID, current_user: User, db: AsyncSession
) -> Finding:
    finding = await db.scalar(select(Finding).where(Finding.id == finding_id))
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if not await can_access_engagement(current_user, finding.engagement_id, db):
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.get("/{finding_id}", response_model=FindingOut)
async def get_finding(
    finding_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    finding = await _get_accessible_finding(finding_id, current_user, db)
    return _out(finding)


@router.patch("/{finding_id}", response_model=FindingOut)
async def update_finding(
    finding_id: UUID,
    body: FindingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    finding = await _get_accessible_finding(finding_id, current_user, db)
    if body.title is not None:
        finding.title = body.title
    if body.severity is not None:
        try:
            finding.severity = FindingSeverity(body.severity)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid severity") from exc
    if body.description is not None:
        finding.description = body.description
    if body.remediation is not None:
        finding.remediation = body.remediation
    if body.status is not None:
        try:
            finding.status = FindingStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid status") from exc
    await AuditService.log(
        db, current_user.id, "finding.update", "finding", finding.id, finding.engagement_id, {}
    )
    await db.commit()
    await db.refresh(finding)
    return _out(finding)


@router.delete("/{finding_id}", status_code=204)
async def delete_finding(
    finding_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    finding = await _get_accessible_finding(finding_id, current_user, db)
    await AuditService.log(
        db, current_user.id, "finding.delete", "finding", finding.id, finding.engagement_id, {}
    )
    await db.delete(finding)
    await db.commit()
    return Response(status_code=204)


@router.post("/{finding_id}/status", response_model=FindingOut)
async def transition_finding_status(
    finding_id: UUID,
    body: FindingStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    finding = await _get_accessible_finding(finding_id, current_user, db)
    try:
        finding.status = FindingStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid status") from exc
    await AuditService.log(
        db,
        current_user.id,
        "finding.status",
        "finding",
        finding.id,
        finding.engagement_id,
        {"status": body.status},
    )
    await db.commit()
    await db.refresh(finding)
    return _out(finding)
