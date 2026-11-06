from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolSpec
from anomaly_tools.base import ToolResult as BaseToolResult


class ToolResult:
    """Legacy result shape kept for compatibility with older executor code."""

    def __init__(self, findings=None):
        self.findings = findings or []


class StubTool:
    name = "stub"
    supported_target_types = ["domain", "ip", "url", "cidr"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        # Stub runs in-process/container placeholder; command is informational.
        target = spec.targets[0] if spec.targets else ""
        return ["stub", target] if target else ["stub"]

    def parse(self, stdout: str) -> BaseToolResult:
        target = stdout.replace("stub reached", "").strip() if stdout else ""
        desc = f"Stub finding for {target}" if target else "Stub finding"
        return BaseToolResult(
            findings=[
                FindingDraft(
                    title="Stub finding: target reachable",
                    severity="info",
                    description=desc,
                )
            ],
            raw=stdout,
        )


def stub_tool(targets=None, **kwargs):
    targets = targets or []
    findings = []
    for t in targets:
        findings.append(
            {
                "title": "Stub finding: target reachable",
                "severity": "info",
                "description": f"Stub finding for {t}",
            }
        )
    if not findings:
        findings.append(
            {
                "title": "Stub finding: target reachable",
                "severity": "info",
                "description": "Stub finding",
            }
        )
    return ToolResult(findings=findings)
