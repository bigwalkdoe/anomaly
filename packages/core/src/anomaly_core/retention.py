from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.config import get_settings
from anomaly_core.models import Evidence, Report


async def purge_expired_records(db: AsyncSession, *, now: datetime | None = None) -> dict[str, int]:
    """Purge expired evidence/reports based on retention settings.

    retention_days <= 0 disables purging for that record type.
    Returns counts of deleted rows.
    """
    settings = get_settings()
    now = now or datetime.now(UTC)
    deleted: dict[str, int] = {"evidence": 0, "reports": 0}

    ev_days = int(getattr(settings, "evidence_retention_days", 0) or 0)
    if ev_days > 0:
        cutoff = now - timedelta(days=ev_days)
        old_ids = (
            await db.scalars(select(Evidence.id).where(Evidence.created_at < cutoff))
        ).all()
        if old_ids:
            await db.execute(delete(Evidence).where(Evidence.id.in_(old_ids)))
            deleted["evidence"] = len(old_ids)

    rep_days = int(getattr(settings, "report_retention_days", 0) or 0)
    if rep_days > 0:
        cutoff = now - timedelta(days=rep_days)
        old_ids = (
            await db.scalars(select(Report.id).where(Report.created_at < cutoff))
        ).all()
        if old_ids:
            await db.execute(delete(Report).where(Report.id.in_(old_ids)))
            deleted["reports"] = len(old_ids)

    if deleted["evidence"] or deleted["reports"]:
        await db.commit()
    return deleted
