from __future__ import annotations

from anomaly_core.models import Engagement, Finding, Run
from anomaly_core.rbac import accessible_engagement_ids
from fastapi import APIRouter
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(user: CurrentUser, db: DbSession):
    allowed = await accessible_engagement_ids(db, user)
    if allowed is not None and not allowed:
        return {
            "overview": {"engagements": 0, "findings": 0, "runs": 0},
            "severity": {"critical": 0, "high": 0},
        }

    eng_q = select(func.count(Engagement.id))
    finding_q = select(func.count(Finding.id))
    run_q = select(func.count(Run.id))
    crit_q = select(func.count(Finding.id)).where(Finding.severity == "critical")
    high_q = select(func.count(Finding.id)).where(Finding.severity == "high")
    if allowed is not None:
        eng_q = eng_q.where(Engagement.id.in_(allowed))
        finding_q = finding_q.where(Finding.engagement_id.in_(allowed))
        run_q = run_q.where(Run.engagement_id.in_(allowed))
        crit_q = crit_q.where(Finding.engagement_id.in_(allowed))
        high_q = high_q.where(Finding.engagement_id.in_(allowed))

    engagements = await db.scalar(eng_q) or 0
    findings = await db.scalar(finding_q) or 0
    runs = await db.scalar(run_q) or 0
    critical = await db.scalar(crit_q) or 0
    high = await db.scalar(high_q) or 0
    return {
        "overview": {"engagements": engagements, "findings": findings, "runs": runs},
        "severity": {"critical": critical, "high": high},
    }
