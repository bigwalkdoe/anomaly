from __future__ import annotations

from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    EngagementStatus,
    OrganizationMember,
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
from anomaly_api.schemas.engagement import (
    EngagementCreate,
    EngagementResponse,
    EngagementUpdate,
    ScopeUpdate,
    TargetCreate,
    TargetResponse,
)

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


@router.get("", response_model=list[EngagementResponse])
async def list_engagements(user: CurrentUser, db: DbSession, limit: int = 100, offset: int = 0):
    if any(r.name == RoleName.admin for r in user.roles):
        engagements = (await db.scalars(select(Engagement).offset(offset).limit(limit))).all()
    else:
        members = (
            await db.scalars(select(EngagementMember).where(EngagementMember.user_id == user.id))
        ).all()
        eng_ids = [m.engagement_id for m in members]
        if not eng_ids:
            return []

        org_memberships = (
            await db.scalars(
                select(OrganizationMember).where(OrganizationMember.user_id == user.id)
            )
        ).all()
        org_ids = {m.organization_id for m in org_memberships}

        engagements = (
            await db.scalars(
                select(Engagement).where(Engagement.id.in_(eng_ids)).offset(offset).limit(limit)
            )
        ).all()
        engagements = [
            e
            for e in engagements
            if getattr(e, "organization_id", None) is None or e.organization_id in org_ids
        ]
    return [EngagementResponse.model_validate(e) for e in engagements]


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(payload: EngagementCreate, user: CurrentUser, db: DbSession):
    organization_id = payload.organization_id
    if organization_id is not None:
        # Allow if global admin or org member
        is_global_admin = any(r.name == RoleName.admin for r in user.roles)
        if not is_global_admin:
            membership = await db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.user_id == user.id,
                )
            )
            if membership is None:
                organization_id = None
    else:
        # Best-effort default org for user (first membership)
        membership = await db.scalar(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        )
        if membership is not None:
            organization_id = membership.organization_id

    engagement = Engagement(
        name=payload.name,
        mode=EngagementMode(payload.mode),
        owner_id=user.id,
        organization_id=organization_id,
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
        organization_id=organization_id,
        metadata={"name": engagement.name},
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return EngagementResponse.model_validate(engagement)


@router.get("/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
):
    return EngagementResponse.model_validate(engagement)


@router.patch("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    payload: EngagementUpdate,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    user: CurrentUser,
    db: DbSession,
):
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        engagement.name = update_data["name"]
    if "status" in update_data:
        engagement.status = EngagementStatus(update_data["status"])
    if "mode" in update_data:
        engagement.mode = EngagementMode(update_data["mode"])
    if "client_name" in update_data:
        engagement.client_name = update_data["client_name"]
    if "rules_of_engagement" in update_data:
        engagement.rules_of_engagement = update_data["rules_of_engagement"]
    await AuditService.log(
        actor_id=user.id,
        action="engagement.update",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata=update_data,
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return EngagementResponse.model_validate(engagement)


@router.delete("/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.admin))
    ],
    user: CurrentUser,
    db: DbSession,
):
    await AuditService.log(
        actor_id=user.id,
        action="engagement.delete",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={},
        db=db,
    )
    await db.delete(engagement)
    await db.commit()
    return None


@router.put("/{engagement_id}/scope")
async def update_scope(
    payload: ScopeUpdate,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    db: DbSession,
):
    scope = engagement.scope
    if scope is None:
        scope = Scope(engagement_id=engagement.id)
        db.add(scope)
        await db.flush()
    # Remove existing entries
    for entry in list(getattr(scope, "entries", [])):
        await db.delete(entry)
    await db.flush()
    for e in payload.entries:
        kind = ScopeEntryKind.in_ if e.kind == "in" else ScopeEntryKind.out
        entry = ScopeEntry(scope_id=scope.id, kind=kind, target_value=e.target_value)
        db.add(entry)
    await db.commit()
    return {"status": "ok"}


@router.post(
    "/{engagement_id}/targets", response_model=TargetResponse, status_code=status.HTTP_201_CREATED
)
async def add_target(
    payload: TargetCreate,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    db: DbSession,
    user: CurrentUser,
):
    target = Target(
        engagement_id=engagement.id,
        value=payload.value,
        type=TargetType(payload.type),
    )
    db.add(target)
    await AuditService.log(
        actor_id=user.id,
        action="target.add",
        resource_type="target",
        resource_id=target.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"value": payload.value, "type": payload.type},
        db=db,
    )
    await db.commit()
    await db.refresh(target)
    return TargetResponse.model_validate(target)
