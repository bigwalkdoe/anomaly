from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class HttpxTool:
    name = "httpx"
    supported_target_types = ["domain", "ip", "url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["httpx", "-silent", "-status-code", "-title"]
        if spec.params.get("follow_redirects"):
            cmd.append("-follow-redirects")
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        for line in stdout.splitlines():
            if line.strip():
                findings.append(
                    FindingDraft(
                        title=f"HTTP response: {line.strip()}",
                        severity="info",
                        description=line.strip(),
                    )
                )
        if not findings:
            findings.append(FindingDraft(title="httpx completed", severity="info"))
        return ToolResult(findings=findings, raw=stdout)
