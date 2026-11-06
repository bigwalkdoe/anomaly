from __future__ import annotations

from typing import Any

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class StubTool:
    name = "stub"
    supported_target_types = ["domain", "ip", "url", "cidr", "service"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        target = spec.targets[0] if spec.targets else ""
        return ["stub", target] if target else ["stub"]

    def parse(self, stdout: str) -> ToolResult:
        target = stdout.replace("stub reached", "").strip() if stdout else ""
        desc = f"Stub finding for {target}" if target else "Stub tool executed successfully."
        return ToolResult(
            findings=[
                FindingDraft(
                    title=f"Stub finding: target reachable ({target})" if target else "Stub finding: target reachable",
                    severity="info",
                    description=desc,
                )
            ],
            raw=stdout,
            stdout=stdout,
            exit_code=0,
        )


async def run_stub(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    target = targets[0] if targets else "unknown"
    stdout = f"stub reached {target}"
    return ToolResult(
        stdout=stdout,
        stderr="",
        exit_code=0,
        parsed_findings=[
            {
                "title": f"Stub finding: target reachable ({target})",
                "severity": "info",
                "description": "Stub tool executed successfully.",
            }
        ],
        findings=[
            {
                "title": f"Stub finding: target reachable ({target})",
                "severity": "info",
                "description": "Stub tool executed successfully.",
            }
        ],
        raw=stdout,
    )


# Back-compat
TOOL_REGISTRY = {"stub": run_stub}
