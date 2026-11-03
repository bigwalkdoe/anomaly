from __future__ import annotations

from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, EngagementMember, EngagementMode, RoleName, Scope
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
    db.add(Scope(engagement_id=engagement.id))
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
