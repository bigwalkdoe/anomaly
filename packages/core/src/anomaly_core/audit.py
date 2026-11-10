from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models import AuditLog


class AuditService:
    @staticmethod
    async def log(
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        engagement_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            engagement_id=engagement_id,
            organization_id=organization_id,
            metadata_=metadata or {},
        )
        if db is not None:
            db.add(entry)
            await db.flush()
            return entry
        raise ValueError("db session required")


async def get_audit_log(
    db: AsyncSession,
    engagement_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
):
    stmt = select(AuditLog)
    if engagement_id is not None:
        stmt = stmt.where(AuditLog.engagement_id == engagement_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    return (await db.scalars(stmt)).all()
