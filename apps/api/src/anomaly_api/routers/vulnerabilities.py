from __future__ import annotations

from anomaly_core.models import Finding, FindingSeverity
from fastapi import APIRouter
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/vulnerabilities", tags=["vulnerabilities"])


@router.get("/summary")
async def summary(user: CurrentUser, db: DbSession):
    total = await db.scalar(select(func.count(Finding.id))) or 0
    critical = (
        await db.scalar(
            select(func.count(Finding.id)).where(Finding.severity == FindingSeverity.critical)
        )
        or 0
    )
    high = (
        await db.scalar(
            select(func.count(Finding.id)).where(Finding.severity == FindingSeverity.high)
        )
        or 0
    )
    medium = (
        await db.scalar(
            select(func.count(Finding.id)).where(Finding.severity == FindingSeverity.medium)
        )
        or 0
    )
    low = (
        await db.scalar(
            select(func.count(Finding.id)).where(Finding.severity == FindingSeverity.low)
        )
        or 0
    )
    return {
        "total": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
    }
