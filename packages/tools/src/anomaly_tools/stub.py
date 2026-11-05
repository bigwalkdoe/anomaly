from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    parsed_findings: list[dict] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


async def run_stub(targets: list[str], params: dict | None = None) -> ToolResult:
    target = targets[0] if targets else "unknown"
    return ToolResult(
        stdout=f"stub reached {target}",
        exit_code=0,
        parsed_findings=[
            {
                "title": f"Stub finding: target reachable ({target})",
                "severity": "info",
                "description": "Stub tool executed successfully.",
            }
        ],
    )


TOOL_REGISTRY = {"stub": run_stub}
