from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class ExecutionManifest:
    """Minimal execution manifest contract for policy-gated, auditable run execution."""

    run_id: str
    organization_id: str | None
    engagement_id: str
    approved_scope_ref: str | None
    tool_id: str
    tool_version: str | None
    targets: list[str]
    params: dict[str, Any]
    resource_limits: dict[str, Any] = field(default_factory=dict)
    expires_at: str | None = None
    output_destination: dict[str, Any] = field(default_factory=dict)
    execution_policy: dict[str, Any] = field(default_factory=dict)
    credentials_ref: str | None = None
    manifest_version: int = 1
    manifest_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _manifest_hash_payload(data: dict[str, Any]) -> str:
    payload = {k: v for k, v in data.items() if k != "manifest_sha256"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_execution_manifest(
    *,
    run_id: uuid.UUID | str,
    engagement,
    tool: str,
    targets: list[str],
    params: dict[str, Any],
    tool_version: str | None = None,
    policy_decision: dict[str, Any] | None = None,
    ttl_minutes: int = 60,
) -> ExecutionManifest:
    org_id = getattr(engagement, "organization_id", None)
    scope = getattr(engagement, "scope", None)
    scope_ref = str(getattr(scope, "id", "")) or None if scope is not None else None
    expires = datetime.now(UTC) + timedelta(minutes=max(1, int(ttl_minutes)))
    manifest = ExecutionManifest(
        run_id=str(run_id),
        organization_id=str(org_id) if org_id else None,
        engagement_id=str(engagement.id),
        approved_scope_ref=scope_ref,
        tool_id=str(tool),
        tool_version=tool_version,
        targets=list(targets),
        params=dict(params or {}),
        resource_limits={},
        expires_at=expires.isoformat(),
        output_destination={},
        execution_policy=policy_decision or {},
        credentials_ref=None,
    )
    data = manifest.to_dict()
    manifest.manifest_sha256 = hashlib.sha256(
        _manifest_hash_payload(data).encode("utf-8")
    ).hexdigest()
    return manifest


def validate_execution_manifest(
    manifest: dict[str, Any] | ExecutionManifest | None,
) -> tuple[bool, str | None]:
    if manifest is None:
        return False, "missing_manifest"
    data = manifest.to_dict() if isinstance(manifest, ExecutionManifest) else dict(manifest)
    required = ("run_id", "engagement_id", "tool_id", "targets")
    for key in required:
        if not data.get(key):
            return False, f"missing_{key}"
    exp = data.get("expires_at")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=UTC)
            if exp_dt < datetime.now(UTC):
                return False, "manifest_expired"
        except Exception:
            return False, "invalid_expires_at"
    recorded = data.get("manifest_sha256")
    if recorded:
        expected = hashlib.sha256(_manifest_hash_payload(data).encode("utf-8")).hexdigest()
        if str(recorded) != expected:
            return False, "manifest_hash_mismatch"
    return True, None
