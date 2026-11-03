from __future__ import annotations

from typing import Annotated

from anomaly_core.models import Engagement, RoleName
from fastapi import APIRouter, Depends

from anomaly_api.deps import require_engagement_access

router = APIRouter(tags=["runs"])


@router.get("/api/engagements/{engagement_id}/runs")
async def list_runs(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
):
    return []
