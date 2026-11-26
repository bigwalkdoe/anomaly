from __future__ import annotations

from typing import Any


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
