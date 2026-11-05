from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models.engagement import Engagement, EngagementMember
from anomaly_core.models.user import Role, RoleName, User, UserRole

ROLE_RANK = {"admin": 3, "pentester": 2, "client_viewer": 1}


async def is_admin(user: User, db: AsyncSession) -> bool:
    result = await db.scalar(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    return result == RoleName.ADMIN


def has_role(user: User, role: str) -> bool:
    # Best-effort sync check; prefer async checks with DB for accuracy.
    return False


def has_permission(user: User, perm: str) -> bool:
    return False


async def engagement_accessible(
    user: User,
    engagement_id: uuid.UUID | str,
    min_role: str,
    db: AsyncSession,
) -> bool:
    if await is_admin(user, db):
        return True
    eid = uuid.UUID(str(engagement_id))
    membership = await db.scalar(
        select(EngagementMember).where(
            EngagementMember.engagement_id == eid,
            EngagementMember.user_id == user.id,
        )
    )
    if membership is None:
        return False
    return ROLE_RANK.get(membership.role, 0) >= ROLE_RANK.get(min_role, 0)


async def can_access_engagement(user: User, engagement_id: uuid.UUID | str, db: AsyncSession) -> bool:
    return await engagement_accessible(user, engagement_id, "client_viewer", db)
