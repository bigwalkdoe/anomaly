from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from anomaly_core.scope import ScopeCheckResult, check_scope

# Params that can relax execution guardrails. Never accept these from untrusted
# suggestion sources such as AI provider output.
RISKY_PARAM_KEYS = {"allow_risky_options", "allow_risky", "risk", "level"}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    scope_result: ScopeCheckResult | None = None

    def to_metadata(
        self,
        *,
        op: str = "assessment.request",
        source: str | None = None,
    ) -> dict[str, Any]:
        """Return JSON-safe audit metadata describing this decision."""
        metadata = dict(self.metadata or {})
        metadata.update({"allowed": self.allowed, "reason": self.reason, "op": op})
        if source is not None:
            metadata["source"] = source
        if self.scope_result is not None:
            metadata.setdefault("targets", [])
            metadata.update(
                {
                    "in_scope": list(self.scope_result.in_scope),
                    "out_of_scope": list(self.scope_result.out_of_scope),
                    "has_warning": self.scope_result.has_warning,
                }
            )
        return metadata


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
    target_list = list(targets)
    if not engagement_approved_for_assessment(engagement):
        status = getattr(engagement, "status", None)
        if status is None:
            status_val = "unknown"
        else:
            status_val = status.value if hasattr(status, "value") else str(status)
        return PolicyDecision(
            allowed=False,
            reason="engagement_not_approved",
            metadata={"status": status_val, "op": "assessment.request"},
        )

    scope_target = scope_engagement or engagement
    scope_result = check_scope(scope_target, target_list)
    if scope_result.has_warning and scope_result.out_of_scope:
        return PolicyDecision(
            allowed=False,
            reason="out_of_scope",
            metadata={"targets": target_list, "out_of_scope": scope_result.out_of_scope},
            scope_result=scope_result,
        )

    return PolicyDecision(
        allowed=True, reason=None, metadata={"targets": target_list}, scope_result=scope_result
    )
