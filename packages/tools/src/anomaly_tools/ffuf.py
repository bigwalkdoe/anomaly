from __future__ import annotations

import json
from typing import Any

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class FfufTool:
    name = "ffuf"
    supported_target_types = ["url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["ffuf", "-silent"]
        wordlist = spec.params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        cmd.extend(["-w", wordlist])
        if spec.targets:
            cmd.extend(["-u", spec.targets[0]])
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        for line in stdout.splitlines():
            if line.strip():
                findings.append(
                    FindingDraft(
                        title=f"Discovered: {line.strip()}",
                        severity="info",
                        description=line.strip(),
                    )
                )
        if not findings:
            findings.append(FindingDraft(title="ffuf completed", severity="info"))
        return ToolResult(findings=findings, raw=stdout)


def parse_ffuf_json(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    """Legacy/compat parser returning ToolResult with parsed_findings (dicts) and discovered_targets."""
    findings: list[dict[str, Any]] = []
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        return ToolResult(
            stdout=output,
            stderr=str(exc),
            exit_code=1,
            parsed_findings=[],
            raw=output,
            findings=[],
            discovered_targets=[],
        )
    for r in data.get("results") or []:
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
    return ToolResult(
        stdout=output,
        stderr="",
        exit_code=0,
        parsed_findings=findings,
        raw=output,
        findings=[],
        discovered_targets=[],
    )
