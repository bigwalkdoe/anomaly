from __future__ import annotations

from anomaly_core.models import Finding, FindingSeverity
from anomaly_core.rbac import accessible_engagement_ids
from fastapi import APIRouter
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/vulnerabilities", tags=["vulnerabilities"])


@router.get("/summary")
async def summary(user: CurrentUser, db: DbSession):
    allowed = await accessible_engagement_ids(db, user)
    if allowed is not None and not allowed:
        return {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}

    def _q(severity: FindingSeverity | None = None):
        q = select(func.count(Finding.id))
        if severity is not None:
            q = q.where(Finding.severity == severity)
        if allowed is not None:
            q = q.where(Finding.engagement_id.in_(allowed))
        return q

    total = await db.scalar(_q()) or 0
    critical = await db.scalar(_q(FindingSeverity.critical)) or 0
    high = await db.scalar(_q(FindingSeverity.high)) or 0
    medium = await db.scalar(_q(FindingSeverity.medium)) or 0
    low = await db.scalar(_q(FindingSeverity.low)) or 0
    return {
        "total": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
    }
