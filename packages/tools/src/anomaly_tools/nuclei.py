from __future__ import annotations

import json
from typing import Any

from anomaly_tools.stub import ToolResult

_SEV_MAP = {
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    "unknown": "info",
}


def parse_nuclei_output(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    findings: list[dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = item.get("info") or {}
        sev = _SEV_MAP.get(str(info.get("severity", "info")).lower(), "info")
        template_id = item.get("template-id") or item.get("templateID") or "nuclei"
        host = item.get("host") or (targets[0] if targets else "")
        matched = item.get("matched-at") or item.get("matched") or host
        findings.append(
            {
                "title": info.get("name") or template_id,
                "severity": sev,
                "description": info.get("description"),
                "remediation": info.get("remediation"),
                "fingerprint": f"nuclei:{template_id}:{matched}",
                "metadata": {"template_id": template_id, "host": host, "matched_at": matched},
            }
        )
    return ToolResult(stdout=output, exit_code=0, parsed_findings=findings)


async def run_nuclei(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    # In-process placeholder; real execution happens in container via runner + parse_nuclei_output.
    return ToolResult(stdout="", exit_code=0, parsed_findings=[])
