from __future__ import annotations

from anomaly_core.models import Engagement, Finding
from anomaly_core.rbac import accessible_engagement_ids
from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search(user: CurrentUser, db: DbSession, q: str = Query(..., min_length=1)):
    allowed = await accessible_engagement_ids(db, user)
    if allowed is not None and not allowed:
        return {"engagements": [], "findings": []}

    eng_q = select(Engagement).where(Engagement.name.ilike(f"%{q}%"))
    finding_q = select(Finding).where(
        or_(Finding.title.ilike(f"%{q}%"), Finding.description.ilike(f"%{q}%"))
    )
    if allowed is not None:
        eng_q = eng_q.where(Engagement.id.in_(allowed))
        finding_q = finding_q.where(Finding.engagement_id.in_(allowed))

    engagements = (await db.scalars(eng_q)).all()
    findings = (await db.scalars(finding_q)).all()
    return {
        "engagements": [{"id": str(e.id), "name": e.name} for e in engagements],
        "findings": [{"id": str(f.id), "title": f.title} for f in findings],
    }
