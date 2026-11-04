from __future__ import annotations

from uuid import UUID

from anomaly_core.audit import get_audit_log
from anomaly_core.models import Engagement, RoleName
from anomaly_core.rbac import engagement_accessible, has_role
from fastapi import APIRouter, HTTPException, Query

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
async def list_audit(
    user: CurrentUser,
    db: DbSession,
    engagement_id: UUID | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = 0,
):
    if engagement_id is not None:
        engagement = await db.get(Engagement, engagement_id)
        if engagement is None:
            raise HTTPException(status_code=404, detail="Engagement not found")
        if has_role(user, RoleName.admin):
            pass
        elif not await engagement_accessible(db, user, engagement):
            raise HTTPException(status_code=403, detail="Forbidden")
        logs = await get_audit_log(db, engagement_id=engagement_id, limit=limit, offset=offset)
    else:
        if not has_role(user, RoleName.admin):
            raise HTTPException(status_code=403, detail="Forbidden")
        logs = await get_audit_log(db, engagement_id=None, limit=limit, offset=offset)
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "engagement_id": str(log.engagement_id) if log.engagement_id else None,
            "metadata": log.metadata,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
