from __future__ import annotations

import hashlib
import json
import uuid


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def finding_fingerprint(
    engagement_id: uuid.UUID,
    title: str,
    description: str = "",
    target: str | None = None,
) -> str:
    """Return a stable, normalized fingerprint for a finding within an engagement.

    Findings with the same normalized content (and target, when present) share a fingerprint,
    allowing manual and tool-produced findings to be deduplicated against each other.
    """
    payload = {
        "engagement_id": str(engagement_id),
        "title": _normalize(title),
        "description": _normalize(description),
        "target": _normalize(target),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
