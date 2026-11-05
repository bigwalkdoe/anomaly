from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field


@dataclass
class ScopeCheckResult:
    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)

    @property
    def has_warning(self) -> bool:
        return bool(self.out_of_scope)


def _normalize(value: str) -> str:
    v = value.strip().lower().rstrip(".")
    return v


def _matches(entry_value: str, target: str) -> bool:
    ev = _normalize(entry_value)
    tv = _normalize(target)
    if ev == tv:
        return True
    # Simple CIDR containment.
    try:
        if "/" in ev:
            net = ipaddress.ip_network(ev, strict=False)
            ip = ipaddress.ip_address(tv.split("/")[0])
            return ip in net
    except ValueError:
        pass
    # Suffix match for subdomains if entry is a domain.
    if tv == ev or tv.endswith("." + ev):
        return True
    return False


def check_scope(entries, requested_targets: list[str]) -> ScopeCheckResult:
    in_entries = [e for e in entries if getattr(e, "kind", None) == "in"]
    out_entries = [e for e in entries if getattr(e, "kind", None) == "out"]
    result = ScopeCheckResult()
    for target in requested_targets:
        # Out-of-scope takes precedence.
        if any(_matches(getattr(e, "target_value", ""), target) for e in out_entries):
            result.out_of_scope.append(target)
            continue
        if in_entries and any(_matches(getattr(e, "target_value", ""), target) for e in in_entries):
            result.in_scope.append(target)
        elif not in_entries:
            # No in-scope list means nothing explicitly allowed; treat as warning.
            result.out_of_scope.append(target)
        else:
            result.out_of_scope.append(target)
    return result
