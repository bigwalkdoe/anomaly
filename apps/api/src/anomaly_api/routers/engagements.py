from __future__ import annotations

from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    EngagementStatus,
    RoleName,
    Scope,
    ScopeEntry,
    ScopeEntryKind,
    Target,
    TargetType,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


@router.get("")
async def list_engagements(user: CurrentUser, db: DbSession):
    if any(r.name == RoleName.admin for r in user.roles):
        engagements = (await db.scalars(select(Engagement))).all()
    else:
        members = (await db.scalars(select(EngagementMember).where(EngagementMember.user_id == user.id))).all()
        eng_ids = [m.engagement_id for m in members]
        if not eng_ids:
            return []
        engagements = (await db.scalars(select(Engagement).where(Engagement.id.in_(eng_ids)))).all()
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "mode": e.mode.value,
            "status": e.status.value,
            "owner_id": str(e.owner_id),
        }
        for e in engagements
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_engagement(payload: dict, user: CurrentUser, db: DbSession):
    engagement = Engagement(
        name=payload.get("name", "Untitled"),
        mode=EngagementMode(payload.get("mode", "own_infra")),
        owner_id=user.id,
    )
    db.add(engagement)
    await db.flush()
    scope = Scope(engagement_id=engagement.id)
    db.add(scope)
    db.add(EngagementMember(engagement_id=engagement.id, user_id=user.id, role=RoleName.admin))
    await AuditService.log(
        actor_id=user.id,
        action="engagement.create",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        metadata={"name": engagement.name},
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return {"id": str(engagement.id), "name": engagement.name}


@router.get("/{engagement_id}")
async def get_engagement(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
):
    return {
        "id": str(engagement.id),
        "name": engagement.name,
        "mode": engagement.mode.value,
        "status": engagement.status.value,
        "owner_id": str(engagement.owner_id),
    }


@router.patch("/{engagement_id}")
async def update_engagement(
    payload: dict,
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    user: CurrentUser,
    db: DbSession,
):
    if "name" in payload:
        engagement.name = payload["name"]
    if "status" in payload:
        engagement.status = EngagementStatus(payload["status"])
    if "mode" in payload:
        engagement.mode = EngagementMode(payload["mode"])
    await AuditService.log(
        actor_id=user.id,
        action="engagement.update",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        metadata=payload,
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return {"id": str(engagement.id), "name": engagement.name, "status": engagement.status.value}


@router.delete("/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.admin))],
    user: CurrentUser,
    db: DbSession,
):
    await AuditService.log(
        actor_id=user.id,
        action="engagement.delete",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        metadata={},
        db=db,
    )
    await db.delete(engagement)
    await db.commit()
    return None


@router.put("/{engagement_id}/scope")
@router.get("/{engagement_id}/scope")
async def update_scope(
    payload: dict = None,
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))] = None,
    db: DbSession = None,
    user: CurrentUser = None,
):
    if payload is None:
        payload = {}
    scope = engagement.scope
    if scope is None:
        scope = Scope(engagement_id=engagement.id)
        db.add(scope)
        await db.flush()
    entries = payload.get("entries", [])
    # Remove existing entries
    for entry in list(getattr(scope, "entries", [])):
        await db.delete(entry)
    await db.flush()
    for e in entries:
        kind = ScopeEntryKind.in_ if e.get("kind") == "in" else ScopeEntryKind.out
        entry = ScopeEntry(scope_id=scope.id, kind=kind, target_value=e.get("target_value") or e.get("value") or "")
        db.add(entry)
    await db.commit()
    return {"status": "ok"}


@router.post("/{engagement_id}/targets", status_code=status.HTTP_201_CREATED)
async def add_target(
    payload: dict,
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    db: DbSession,
    user: CurrentUser,
):
    target = Target(
        engagement_id=engagement.id,
        value=payload.get("value", ""),
        type=TargetType(payload.get("type", "domain")),
    )
    db.add(target)
    await AuditService.log(
        actor_id=user.id,
        action="target.add",
        resource_type="target",
        resource_id=target.id,
        engagement_id=engagement.id,
        metadata=payload,
        db=db,
    )
    await db.commit()
    await db.refresh(target)
    return {"id": str(target.id), "value": target.value}
