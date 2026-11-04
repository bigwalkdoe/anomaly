from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class SqlmapTool:
    name = "sqlmap"
    supported_target_types = ["url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["sqlmap", "--batch", "--banner"]
        if spec.params.get("level"):
            cmd.extend(["--level", str(spec.params["level"])])
        if spec.params.get("risk"):
            cmd.extend(["--risk", str(spec.params["risk"])])
        if spec.targets:
            cmd.extend(["-u", spec.targets[0]])
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        if "sqlmap identified" in stdout.lower() or "vulnerable" in stdout.lower():
            findings.append(FindingDraft(title="SQL injection detected", severity="high", description=stdout[:500]))
        if not findings:
            findings.append(FindingDraft(title="sqlmap completed", severity="info", description="Scan completed"))
        return ToolResult(findings=findings, raw=stdout)
