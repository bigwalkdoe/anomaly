from __future__ import annotations

from uuid import UUID

from anomaly_core.models import AuditLog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def recorded_report_sha256(db: AsyncSession, report_id: UUID) -> str | None:
    """Return the checksum recorded when a report was generated, if available."""
    rows = (
        await db.scalars(
            select(AuditLog)
            .where(
                AuditLog.action == "report.generate",
                AuditLog.resource_id == report_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
    ).all()
    for row in rows:
        sha = (row.metadata or {}).get("report_sha256")
        if sha:
            return str(sha)
    return None


def report_verification(content_sha: str | None, recorded_sha: str | None) -> str:
    if not content_sha or not recorded_sha:
        return "unavailable"
    return "match" if content_sha == recorded_sha else "mismatch"
