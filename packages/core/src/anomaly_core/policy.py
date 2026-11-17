from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from anomaly_core.scope import ScopeCheckResult, check_scope


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    scope_result: ScopeCheckResult | None = None


def engagement_approved_for_assessment(engagement) -> bool:
    status = getattr(engagement, "status", None)
    if status is None:
        return True
    status_val = status.value if hasattr(status, "value") else str(status)
    return status_val in ("approved", "active")


def evaluate_assessment_request(
    engagement,
    targets: Iterable[str],
    *,
    scope_engagement=None,
) -> PolicyDecision:
    """Evaluate whether an assessment/run request is authorized by engagement state and scope.

    `scope_engagement` should be the engagement instance loaded with scope/entries for
    accurate scope evaluation; falls back to `engagement`.
    """
    if not engagement_approved_for_assessment(engagement):
        status = getattr(engagement, "status", None)
        status_val = status.value if hasattr(status, "value") else str(status)
        return PolicyDecision(
            allowed=False,
            reason="engagement_not_approved",
            metadata={"status": status_val, "op": "assessment.request"},
        )

    scope_target = scope_engagement or engagement
    scope_result = check_scope(scope_target, targets)
    if scope_result.has_warning and scope_result.out_of_scope:
        return PolicyDecision(
            allowed=False,
            reason="out_of_scope",
            metadata={"targets": list(targets), "out_of_scope": scope_result.out_of_scope},
            scope_result=scope_result,
        )

    return PolicyDecision(allowed=True, reason=None, metadata={}, scope_result=scope_result)
