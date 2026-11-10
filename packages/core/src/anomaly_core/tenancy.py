from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.models.tenancy import Membership, Organization
from anomaly_core.models.user import User


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "org"


async def get_or_create_default_organization(db: AsyncSession, user: User) -> Organization:
    """Ensure the user has at least one organization membership; create a default org if missing."""
    existing = await db.scalar(
        select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at.asc())
    )
    if existing is not None:
        org = await db.get(Organization, existing.organization_id)
        if org is not None:
            return org
    base = _slugify(user.email.split("@")[0] if user.email else str(user.id))
    slug = f"{base}-{str(user.id)[:8]}"
    org = Organization(name=f"{user.name or base}'s Organization", slug=slug)
    db.add(org)
    await db.flush()
    db.add(
        Membership(
            user_id=user.id,
            organization_id=org.id,
            workspace_id=None,
            role="owner",
        )
    )
    await db.flush()
    return org


async def get_user_memberships(db: AsyncSession, user: User) -> list[Membership]:
    rows = (await db.scalars(select(Membership).where(Membership.user_id == user.id))).all()
    if not rows:
        await get_or_create_default_organization(db, user)
        rows = (await db.scalars(select(Membership).where(Membership.user_id == user.id))).all()
    return list(rows)


async def user_in_organization(db: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
    row = await db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        )
    )
    return row is not None

