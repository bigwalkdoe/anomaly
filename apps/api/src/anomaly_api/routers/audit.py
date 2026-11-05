from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db
from anomaly_core.audit import get_audit_log
from anomaly_core.models.user import User
from anomaly_core.rbac import can_access_engagement, is_admin

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    engagement_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    if engagement_id and not await is_admin(current_user, db):
        if not await can_access_engagement(current_user, engagement_id, db):
            raise HTTPException(status_code=403, detail="Forbidden")
    if engagement_id is None and not await is_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = await get_audit_log(db, engagement_id=engagement_id, limit=limit, offset=offset)
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": str(r.resource_id) if r.resource_id else None,
            "engagement_id": str(r.engagement_id) if r.engagement_id else None,
            "metadata": r.meta,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
