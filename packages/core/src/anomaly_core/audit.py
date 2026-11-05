from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models.audit import AuditLog


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        actor_id: uuid.UUID | str | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | str | None = None,
        engagement_id: uuid.UUID | str | None = None,
        metadata: dict | None = None,
        commit: bool = False,
    ) -> AuditLog:
        row = AuditLog(
            actor_id=uuid.UUID(str(actor_id)) if actor_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=uuid.UUID(str(resource_id)) if resource_id else None,
            engagement_id=uuid.UUID(str(engagement_id)) if engagement_id else None,
            meta=metadata or {},
        )
        db.add(row)
        await db.flush()
        if commit:
            await db.commit()
        return row


async def get_audit_log(
    db: AsyncSession,
    engagement_id: uuid.UUID | str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if engagement_id:
        stmt = stmt.where(AuditLog.engagement_id == uuid.UUID(str(engagement_id)))
    result = await db.scalars(stmt)
    return list(result)
