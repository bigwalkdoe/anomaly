from __future__ import annotations

import json
from typing import Any

from anomaly_tools.base import ToolResult, ToolSpec


class FfufTool:
    name = "ffuf"
    supported_target_types = ["url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["ffuf", "-of", "json"]
        params = spec.params or {}
        wordlist = params.get("wordlist", "/usr/share/wordlists/common.txt")
        cmd.extend(["-w", str(wordlist)])
        if spec.targets:
            cmd.extend(["-u", spec.targets[0]])
        return cmd

    def parse(self, stdout: str, targets: list[str] | None = None, params: dict[str, Any] | None = None) -> ToolResult:
        return parse_ffuf_json(stdout, targets, params)


def parse_ffuf_json(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    findings: list[dict[str, Any]] = []
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        return ToolResult(stdout=output, stderr=str(exc), exit_code=1, parsed_findings=[], raw=output)
    for r in (data.get("results") or []):
        url = r.get("url") or r.get("input", {}).get("FUZZ") or "unknown"
        status = r.get("status")
        length = r.get("length")
        severity = "info"
        path = str(url).lower()
        if status == 200 and any(
            x in path for x in ["/admin", "/login", "/.git", "/config", "/api"]
        ):
            severity = "low"
        elif status in (401, 403) and any(x in path for x in ["/.git", "/admin", "/backup"]):
            severity = "info"
        findings.append(
            {
                "title": f"ffuf found {url} (HTTP {status})",
                "severity": severity,
                "description": f"status={status} length={length}",
                "fingerprint": f"ffuf:{url}:{status}",
                "metadata": {"url": url, "status": status, "length": length},
            }
        )
    return ToolResult(stdout=output, exit_code=0, parsed_findings=findings, raw=output)


async def run_ffuf(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    return ToolResult(stdout="", exit_code=0, parsed_findings=[])

