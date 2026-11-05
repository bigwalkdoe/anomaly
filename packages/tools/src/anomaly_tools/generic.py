from __future__ import annotations

from typing import Any

from anomaly_tools.stub import ToolResult


def parse_passthrough(
    stdout: str, stderr: str, exit_code: int, targets: list[str], params: dict[str, Any] | None
) -> ToolResult:
    # Placeholder: preserve output as evidence; structured parsing added per tool.
    return ToolResult(stdout=stdout, stderr=stderr, exit_code=exit_code, parsed_findings=[])


async def run_not_implemented(
    targets: list[str], params: dict[str, Any] | None = None
) -> ToolResult:
    return ToolResult(
        stdout="", stderr="tool parser not implemented", exit_code=0, parsed_findings=[]
    )
