from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db, require_engagement_access
from anomaly_core.audit import AuditService
from anomaly_core.models.engagement import Engagement, EngagementMode
from anomaly_core.models.finding import Finding
from anomaly_core.models.user import User
from anomaly_core.rbac import is_admin

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


class EngagementOut(BaseModel):
    id: str
    name: str
    mode: str
    status: str


class EngagementCreate(BaseModel):
    name: str
    mode: str
    client_name: str | None = None
    rules_of_engagement: str | None = None


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
    eng = Engagement(name=body.name, mode=mode, owner_id=current_user.id, client_name=body.client_name)
    db.add(eng)
    await db.flush()
    await AuditService.log(
        db,
        actor_id=current_user.id,
        action="engagement.create",
        resource_type="engagement",
        resource_id=eng.id,
        engagement_id=eng.id,
        metadata={"name": eng.name},
    )
    await db.commit()
    return EngagementOut(id=str(eng.id), name=eng.name, mode=eng.mode.value, status=eng.status.value)



@router.get("/{engagement_id}", response_model=EngagementOut)
async def get_engagement(
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
) -> EngagementOut:
    return EngagementOut(id=str(eng.id), name=eng.name, mode=eng.mode.value, status=eng.status.value)


@router.get("/{engagement_id}/findings")
async def list_engagement_findings(
    engagement_id: UUID,
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    rows = await db.scalars(select(Finding).where(Finding.engagement_id == eng.id))
    return [{"id": str(r.id), "title": r.title} for r in rows]
