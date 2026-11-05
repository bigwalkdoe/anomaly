from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db, require_engagement_access
from anomaly_api.schemas.engagement import (
    EngagementCreate,
    EngagementOut,
    EngagementUpdate,
    ScopeOut,
    ScopePut,
    TargetCreate,
)
from anomaly_api.schemas.finding import FindingCreate, FindingOut
from anomaly_core.models.finding import Finding, FindingSeverity, FindingStatus
from anomaly_core.audit import AuditService
from anomaly_core.models.engagement import (
    Engagement,
    EngagementMember,
    EngagementMode,
    EngagementStatus,
    Scope,
    ScopeEntry,
    Target,
)
from anomaly_core.models.user import User
from anomaly_core.rbac import is_admin

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


def _eng_out(eng: Engagement) -> EngagementOut:
    return EngagementOut(
        id=str(eng.id),
        name=eng.name,
        mode=eng.mode.value,
        status=eng.status.value,
        client_name=eng.client_name,
    )


@router.get("", response_model=list[EngagementOut])
async def list_engagements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EngagementOut]:
    if await is_admin(current_user, db):
        rows = await db.scalars(select(Engagement))
    else:
        rows = await db.scalars(
            select(Engagement)
            .join(EngagementMember, EngagementMember.engagement_id == Engagement.id)
            .where(EngagementMember.user_id == current_user.id)
        )
    return [_eng_out(r) for r in rows]


@router.post("", response_model=EngagementOut, status_code=201)
async def create_engagement(
    body: EngagementCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EngagementOut:
    if not await is_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        mode = EngagementMode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid mode") from exc
    eng = Engagement(
        name=body.name,
        mode=mode,
        owner_id=current_user.id,
        client_name=body.client_name,
        rules_of_engagement=body.rules_of_engagement,
    )
    db.add(eng)
    await db.flush()
    await AuditService.log(
        db, current_user.id, "engagement.create", "engagement", eng.id, eng.id, {"name": eng.name}
    )
    await db.commit()
    return _eng_out(eng)


@router.get("/{engagement_id}", response_model=EngagementOut)
async def get_engagement(
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
) -> EngagementOut:
    return _eng_out(eng)


@router.patch("/{engagement_id}", response_model=EngagementOut)
async def update_engagement(
    body: EngagementUpdate,
    eng: Annotated[Engagement, Depends(require_engagement_access("pentester"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EngagementOut:
    if body.name is not None:
        eng.name = body.name
    if body.status is not None:
        try:
            eng.status = EngagementStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid status") from exc
    if body.client_name is not None:
        eng.client_name = body.client_name
    if body.rules_of_engagement is not None:
        eng.rules_of_engagement = body.rules_of_engagement
    await AuditService.log(db, current_user.id, "engagement.update", "engagement", eng.id, eng.id, {})
    await db.commit()
    await db.refresh(eng)
    return _eng_out(eng)


@router.delete("/{engagement_id}", status_code=204)
async def delete_engagement(
    eng: Annotated[Engagement, Depends(require_engagement_access("pentester"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await AuditService.log(db, current_user.id, "engagement.delete", "engagement", eng.id, eng.id, {})
    await db.delete(eng)
    await db.commit()
    return Response(status_code=204)


@router.get("/{engagement_id}/scope", response_model=ScopeOut)
async def get_scope(
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScopeOut:
    scope = await db.scalar(select(Scope).where(Scope.engagement_id == eng.id))
    if scope is None:
        return ScopeOut()
    entries = await db.scalars(select(ScopeEntry).where(ScopeEntry.scope_id == scope.id))
    ins, outs = [], []
    for e in entries:
        (ins if e.kind == "in" else outs).append(e.target_value)
    return ScopeOut(notes=scope.notes, in_scope=ins, out_of_scope=outs)


@router.put("/{engagement_id}/scope", response_model=ScopeOut)
async def put_scope(
    body: ScopePut,
    eng: Annotated[Engagement, Depends(require_engagement_access("pentester"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScopeOut:
    scope = await db.scalar(select(Scope).where(Scope.engagement_id == eng.id))
    if scope is None:
        scope = Scope(engagement_id=eng.id, notes=body.notes)
        db.add(scope)
        await db.flush()
    else:
        scope.notes = body.notes
        existing = await db.scalars(select(ScopeEntry).where(ScopeEntry.scope_id == scope.id))
        for e in existing:
            await db.delete(e)
        await db.flush()
    for v in body.in_scope:
        db.add(ScopeEntry(scope_id=scope.id, kind="in", target_value=v))
    for v in body.out_of_scope:
        db.add(ScopeEntry(scope_id=scope.id, kind="out", target_value=v))
    await AuditService.log(db, current_user.id, "scope.update", "scope", scope.id, eng.id, {})
    await db.commit()
    return ScopeOut(notes=scope.notes, in_scope=body.in_scope, out_of_scope=body.out_of_scope)


@router.post("/{engagement_id}/targets", status_code=201)
async def add_target(
    body: TargetCreate,
    eng: Annotated[Engagement, Depends(require_engagement_access("pentester"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    target = Target(
        engagement_id=eng.id,
        value=body.value,
        type=body.type,
        status=body.status,
        discovered=body.discovered,
    )
    db.add(target)
    await db.flush()
    await AuditService.log(db, current_user.id, "target.create", "target", target.id, eng.id, {})
    await db.commit()
    return {"id": str(target.id), "value": target.value, "type": target.type}


@router.get("/{engagement_id}/findings")
async def list_engagement_findings(
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    rows = await db.scalars(select(Finding).where(Finding.engagement_id == eng.id))
    return [
        {
            "id": str(r.id),
            "engagement_id": str(r.engagement_id),
            "title": r.title,
            "severity": r.severity.value,
            "status": r.status.value,
            "description": r.description,
        }
        for r in rows
    ]


@router.post("/{engagement_id}/findings", response_model=FindingOut, status_code=201)
async def create_finding(
    body: FindingCreate,
    eng: Annotated[Engagement, Depends(require_engagement_access("pentester"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    try:
        severity = FindingSeverity(body.severity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid severity") from exc
    finding = Finding(
        engagement_id=eng.id,
        title=body.title,
        severity=severity,
        status=FindingStatus.NEW,
        description=body.description,
        remediation=body.remediation,
        reporter_id=current_user.id,
        target_id=UUID(body.target_id) if body.target_id else None,
        fingerprint=f"{eng.id}:{body.title}",
    )
    db.add(finding)
    await db.flush()
    await AuditService.log(db, current_user.id, "finding.create", "finding", finding.id, eng.id, {})
    await db.commit()
    await db.refresh(finding)
    return FindingOut(
        id=str(finding.id),
        engagement_id=str(finding.engagement_id),
        title=finding.title,
        severity=finding.severity.value,
        status=finding.status.value,
        description=finding.description,
    )
