from __future__ import annotations

from anomaly_core.models import Engagement, Finding, Run
from fastapi import APIRouter
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(user: CurrentUser, db: DbSession):
    engagements = await db.scalar(select(func.count(Engagement.id))) or 0
    findings = await db.scalar(select(func.count(Finding.id))) or 0
    runs = await db.scalar(select(func.count(Run.id))) or 0
    critical = await db.scalar(select(func.count(Finding.id)).where(Finding.severity == "critical")) or 0
    high = await db.scalar(select(func.count(Finding.id)).where(Finding.severity == "high")) or 0
    return {
        "overview": {"engagements": engagements, "findings": findings, "runs": runs},
        "severity": {"critical": critical, "high": high},
    }
