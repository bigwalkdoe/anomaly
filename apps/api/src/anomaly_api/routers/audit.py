from __future__ import annotations

from typing import Annotated
from uuid import UUID

from anomaly_core.audit import get_audit_log
from anomaly_core.models import AuditLog, Engagement, Membership, RoleName
from anomaly_core.rbac import engagement_accessible, has_role
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
async def list_audit(
    user: CurrentUser,
    db: DbSession,
    engagement_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query()] = 100,
    offset: int = 0,
):
    if engagement_id is not None:
        engagement = await db.get(Engagement, engagement_id)
        if engagement is None:
            raise HTTPException(status_code=404, detail="Engagement not found")
        if not await engagement_accessible(db, user, engagement):
            raise HTTPException(status_code=404, detail="Engagement not found")
        logs = await get_audit_log(db, engagement_id=engagement_id, limit=limit, offset=offset)
    else:
        if not has_role(user, RoleName.admin):
            raise HTTPException(status_code=403, detail="Forbidden")
        org_rows = (
            await db.scalars(
                select(Membership.organization_id).where(Membership.user_id == user.id)
            )
        ).all()
        org_ids = [oid for oid in org_rows if oid is not None]
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        if org_ids:
            stmt = stmt.where(
                or_(AuditLog.organization_id.in_(org_ids), AuditLog.organization_id.is_(None))
            )
        else:
            stmt = stmt.where(AuditLog.organization_id.is_(None))
        logs = (await db.scalars(stmt)).all()
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
