from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Protocol


@dataclass
class FindingDraft:
    title: str
    severity: str = "info"
    description: str = ""
    remediation: str | None = None
    cvss: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _finding_to_dict(f: Any) -> dict[str, Any]:
    if isinstance(f, dict):
        return f
    if isinstance(f, FindingDraft):
        return asdict(f)
    if is_dataclass(f) and not isinstance(f, type):
        return asdict(f)
    if hasattr(f, "__dict__"):
        return dict(f.__dict__)
    return {"title": str(f), "severity": "info", "description": ""}


@dataclass
class ToolResult:
    findings: list[Any] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw: str = ""
    discovered_targets: list[dict[str, Any]] = field(default_factory=list)
    # feat/worker compat
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    artifacts: list[str] = field(default_factory=list)
    parsed_findings: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        # Normalize: accept parsed_findings= (feat) or findings= (plan)
        if self.parsed_findings is not None and not self.findings:
            self.findings = list(self.parsed_findings)
        # Keep raw/stdout coherent when only one is provided
        if self.raw and not self.stdout:
            self.stdout = self.raw
        elif self.stdout and not self.raw:
            self.raw = self.stdout
        # Materialize parsed_findings as dict view for feat tests/code
        if self.parsed_findings is None:
            self.parsed_findings = [_finding_to_dict(f) for f in self.findings]
        else:
            # ensure findings populated too
            if not self.findings:
                self.findings = list(self.parsed_findings)

    def finding_dicts(self) -> list[dict[str, Any]]:
        return [_finding_to_dict(f) for f in self.findings]


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

    def parse(
        self,
        stdout: str,
        targets: list[str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:  # pragma: no cover
        ...
