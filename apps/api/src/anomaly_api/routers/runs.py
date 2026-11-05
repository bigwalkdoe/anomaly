from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from anomaly_api.deps import get_current_user, get_db, require_engagement_access
from anomaly_core.models.engagement import Engagement
from anomaly_core.models.user import User
from anomaly_core.rbac import is_admin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models.engagement import EngagementMember

router = APIRouter(prefix="/api/engagements", tags=["runs"])


class RunCreate(BaseModel):
    tool: str
    targets: list[str] = []


@router.post("/{engagement_id}/runs", status_code=202)
async def create_run(
    engagement_id: UUID,
    body: RunCreate,
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Client viewers cannot create runs.
    if await is_admin(current_user, db):
        pass
    else:
        member = await db.scalar(
            select(EngagementMember).where(
                EngagementMember.engagement_id == engagement_id,
                EngagementMember.user_id == current_user.id,
            )
        )
        if member is None or member.role == "client_viewer":
            raise HTTPException(status_code=403, detail="Forbidden")
    return {"id": "pending", "status": "queued"}
