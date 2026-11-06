from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class FindingDraft:
    title: str
    severity: str = "info"
    description: str = ""
    remediation: str | None = None
    cvss: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    findings: list[FindingDraft] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw: str = ""


@dataclass
class ToolSpec:
    targets: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    engagement_id: str | None = None


class Tool(Protocol):
    name: str
    supported_target_types: list[str]

    def build_cmd(self, spec: ToolSpec) -> list[str]:  # pragma: no cover
        ...

    def parse(self, stdout: str) -> ToolResult:  # pragma: no cover
        ...
