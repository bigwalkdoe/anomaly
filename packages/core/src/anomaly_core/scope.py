from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class ScopeCheckResult:
    in_scope: list[str]
    out_of_scope: list[str]
    has_warning: bool


def _normalize_target(target: str) -> str:
    t = str(target).strip().lower()
    if t.endswith("."):
        t = t.rstrip(".")
    return t


def check_scope(engagement, requested_targets: Iterable[str], scope_entries=None, db=None) -> ScopeCheckResult:
    normalized_requested = [_normalize_target(t) for t in requested_targets]

    in_scope_entries: list[str] = []
    out_scope_entries: list[str] = []

    # Try to get from passed scope_entries first
    if scope_entries is not None:
        for entry in scope_entries:
            try:
                val = _normalize_target(getattr(entry, "target_value", entry))
                kind = getattr(entry, "kind", None)
                kind_str = str(kind)
                if "out" in kind_str:
                    out_scope_entries.append(val)
                    continue
                if "in" in kind_str and "out" not in kind_str:
                    in_scope_entries.append(val)
                    continue
            except Exception:
                continue
    else:
        try:
            scope = getattr(engagement, "scope", None)
            if scope is not None:
                entries = []
                try:
                    entries = scope.entries
                except Exception:
                    try:
                        entries = getattr(scope, "entries", [])
                    except Exception:
                        entries = []
                if hasattr(entries, "__await__"):
                    entries = []
                for entry in entries or []:
                    try:
                        val = _normalize_target(getattr(entry, "target_value", ""))
                        kind = getattr(entry, "kind")
                        kind_str = str(kind)
                        if "out" in kind_str:
                            out_scope_entries.append(val)
                            continue
                        if "ScopeEntryKind.in_" in kind_str or (getattr(kind, "value", None) == "in"):
                            in_scope_entries.append(val)
                            continue
                    except Exception:
                        continue
        except Exception:
            pass

    in_scope: list[str] = []
    out_of_scope: list[str] = []

    # If there are explicit scope entries defined, enforce them strictly
    if in_scope_entries or out_scope_entries:
        for t in normalized_requested:
            if t in out_scope_entries:
                out_of_scope.append(t)
                continue
            if in_scope_entries:
                is_in = False
                for i in in_scope_entries:
                    if not i:
                        continue
                    if t == i or t.endswith("." + i) or i.endswith("." + t):
                        is_in = True
                        break
                if is_in:
                    in_scope.append(t)
                else:
                    out_of_scope.append(t)
            else:
                out_of_scope.append(t)  # if only out-of-scope defined, others might be in scope? depends
    else:
        # No explicit scope defined - warn on everything per warn-and-log behavior
        for t in normalized_requested:
            out_of_scope.append(t)
            # also put in in_scope? test says "scope_warning=true" and logged as warning

    return ScopeCheckResult(
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        has_warning=len(out_of_scope) > 0,
    )


async def record_scope_warning(*args, **kwargs):
    from anomaly_core import audit

    return await audit.AuditService.log(*args, **kwargs)


def parse_cidr(cidr: str):
    """Basic CIDR parsing stub"""
    return cidr
