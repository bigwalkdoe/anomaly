from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models import Organization, OrganizationMember, User


async def get_org_membership(
    db: AsyncSession, user: User, organization_id: uuid.UUID
) -> OrganizationMember | None:
    return await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    )


async def user_in_org(db: AsyncSession, user: User, organization_id: uuid.UUID) -> bool:
    # Platform admins may access across orgs (legacy/global admin role).
    if any(getattr(role, "name", None) and str(role.name) == "admin" for role in user.roles):
        return True
    return (await get_org_membership(db, user, organization_id)) is not None


async def get_organization(db: AsyncSession, organization_id: uuid.UUID) -> Organization | None:
    return await db.get(Organization, organization_id)
