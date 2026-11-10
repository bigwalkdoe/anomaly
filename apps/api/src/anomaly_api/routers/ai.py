from __future__ import annotations

from uuid import UUID

from anomaly_ai import AIService, get_provider
from anomaly_core.models import Engagement
from anomaly_core.rbac import engagement_accessible
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/ai", tags=["ai"])


class SuggestToolsRequest(BaseModel):
    objective: str = Field(..., min_length=1)
    context: dict | None = None
    engagement_id: UUID | None = None


@router.post("/suggest-tools")
async def suggest_tools(payload: SuggestToolsRequest, user: CurrentUser, db: DbSession):
    engagement_id = payload.engagement_id
    if engagement_id is not None:
        engagement = await db.get(Engagement, engagement_id)
        if engagement is None or not await engagement_accessible(db, user, engagement):
            # Match existing behavior: avoid leaking existence
            raise HTTPException(status_code=404, detail="Engagement not found")

    svc = AIService(provider=get_provider(), db=db)
    try:
        result = await svc.suggest_tools(
            objective=payload.objective,
            context=payload.context,
            actor_id=getattr(user, "id", None),
            engagement_id=engagement_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc
    return result
