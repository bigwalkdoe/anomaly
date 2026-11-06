from __future__ import annotations

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
            if line:
                findings.append(
                    FindingDraft(title="nuclei finding", severity="medium", description=line)
                )
        if not findings:
            findings.append(FindingDraft(title="nuclei scan completed", severity="info"))
        return ToolResult(findings=findings, raw=stdout)
