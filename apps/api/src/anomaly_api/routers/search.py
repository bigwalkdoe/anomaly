from __future__ import annotations

from anomaly_core.models import Engagement, Finding
from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search(user: CurrentUser, db: DbSession, q: str = Query(..., min_length=1)):
    engagements = (await db.scalars(select(Engagement).where(Engagement.name.ilike(f"%{q}%")))).all()
    findings = (await db.scalars(select(Finding).where(or_(Finding.title.ilike(f"%{q}%"), Finding.description.ilike(f"%{q}%"))))).all()
    return {
        "engagements": [{"id": str(e.id), "name": e.name} for e in engagements],
        "findings": [{"id": str(f.id), "title": f.title} for f in findings],
    }
