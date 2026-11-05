from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_db, get_current_user, require_engagement_access
from anomaly_core.models.engagement import Engagement
from anomaly_core.models.finding import Finding
from anomaly_core.models.user import User
from anomaly_core.rbac import is_admin

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


class EngagementOut(BaseModel):
    id: str
    name: str
    mode: str
    status: str


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
