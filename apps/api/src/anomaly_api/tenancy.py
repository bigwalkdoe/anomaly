from __future__ import annotations

from typing import Any
from uuid import UUID

from anomaly_core.models import Engagement, Organization, User
from anomaly_core.tenancy import get_or_create_default_organization, get_user_memberships
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def child_organization_matches_engagement(child: Any, engagement: Any) -> bool:
    """Return whether a child row's org agrees with its parent engagement's org.

    Legacy rows may have a null org on either side; those remain compatible. A mismatch
    between two non-null org ids indicates corrupted or migrated data and must not be
    served through an engagement that the caller can otherwise access.
    """
    child_org = getattr(child, "organization_id", None)
    engagement_org = getattr(engagement, "organization_id", None)
    if child_org is None or engagement_org is None:
        return True
    return child_org == engagement_org


def child_organization_matches_engagement_sql(child_cls: Any) -> Any:
    """SQL predicate equivalent of the org-consistency check for engagement children."""
    engagement_org = (
        select(Engagement.organization_id)
        .where(Engagement.id == child_cls.engagement_id)
        .scalar_subquery()
    )
    return or_(
        child_cls.organization_id.is_(None),
        engagement_org.is_(None),
        child_cls.organization_id == engagement_org,
    )


async def resolve_creation_organization(
    db: AsyncSession, user: User, requested_org_id: UUID | None
) -> Organization:
    """Resolve the org for a new resource, rejecting orgs the caller is not a member of."""
    if requested_org_id is None:
        return await get_or_create_default_organization(db, user)

    memberships = await get_user_memberships(db, user)
    allowed = {m.organization_id for m in memberships if m.organization_id is not None}
    if requested_org_id not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
    org = await db.get(Organization, requested_org_id)
    if org is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    return org
