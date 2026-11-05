from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db
from anomaly_core.models.finding import Finding
from anomaly_core.models.user import User
from anomaly_core.rbac import can_access_engagement

router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.get("/{finding_id}")
async def get_finding(
    finding_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    finding = await db.scalar(select(Finding).where(Finding.id == finding_id))
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if not await can_access_engagement(current_user, finding.engagement_id, db):
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"id": str(finding.id), "title": finding.title}
