from __future__ import annotations

import json
from typing import Any

from anomaly_tools.stub import ToolResult


def _target_type(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return "url"
    if "/" in value:
        return "endpoint"
    return "domain"


def parse_recon_output(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    discovered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = item.get("url") or item.get("host") or item.get("input")
        if not value:
            continue
        value = str(value)
        if value in seen:
            continue
        seen.add(value)
        discovered.append(
            {
                "value": value,
                "type": _target_type(value),
                "status": "discovered",
                "discovered": True,
                "metadata": {
                    k: v for k, v in item.items() if k in ("status_code", "host", "port", "title")
                },
            }
        )
    return ToolResult(stdout=output, exit_code=0, parsed_findings=[], discovered_targets=discovered)


async def run_recon(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    return ToolResult(stdout="", exit_code=0, parsed_findings=[], discovered_targets=[])
