from __future__ import annotations

import json
from typing import Any

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class NucleiTool:
    name = "nuclei"
    supported_target_types = ["domain", "ip", "url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["nuclei", "-jsonl", "-silent"]
        severity = spec.params.get("severity")
        if severity:
            cmd.extend(["-severity", str(severity)])
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                findings.append(
                    FindingDraft(title="nuclei finding", severity="medium", description=line)
                )
                continue
            info = item.get("info") or {}
            sev = str(info.get("severity", "info")).lower()
            if sev not in ("info", "low", "medium", "high", "critical"):
                sev = "info"
            template_id = item.get("template-id") or item.get("templateID") or "nuclei"
            host = item.get("host") or ""
            matched = item.get("matched-at") or item.get("matched") or host
            findings.append(
                FindingDraft(
                    title=info.get("name") or template_id,
                    severity=sev,
                    description=info.get("description") or "",
                    remediation=info.get("remediation"),
                    metadata={
                        "fingerprint": f"nuclei:{template_id}:{matched}",
                        "template_id": template_id,
                        "host": host,
                        "matched_at": matched,
                    },
                )
            )
        if not findings:
            findings.append(FindingDraft(title="nuclei scan completed", severity="info"))
        return ToolResult(findings=findings, raw=stdout)


def parse_nuclei_output(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    """Legacy/compat parser returning ToolResult with parsed_findings (dicts) and discovered_targets."""
    findings: list[dict[str, Any]] = []
    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = item.get("info") or {}
        sev = str(info.get("severity", "info")).lower()
        if sev not in ("info", "low", "medium", "high", "critical"):
            sev = "info"
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
    return ToolResult(
        stdout=output or "",
        stderr="",
        exit_code=0,
        parsed_findings=findings,
        raw=output or "",
        findings=[],
        discovered_targets=[],
    )
