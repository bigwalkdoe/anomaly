from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class SqlmapTool:
    name = "sqlmap"
    supported_target_types = ["url"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        # Safe defaults: detection-oriented, non-interactive.
        cmd = ["sqlmap", "--batch", "--banner"]
        # Risky tuning options require explicit opt-in and must be audited by the caller.
        if spec.params.get("allow_risky_options"):
            if spec.params.get("level") is not None:
                cmd.extend(["--level", str(spec.params["level"])])
            if spec.params.get("risk") is not None:
                cmd.extend(["--risk", str(spec.params["risk"])])
        if spec.targets:
            cmd.extend(["-u", spec.targets[0]])
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        low = stdout.lower()
        if "sqlmap identified" in low or "vulnerable" in low:
            findings.append(
                FindingDraft(
                    title="SQL injection detected",
                    severity="high",
                    description=stdout[:500],
                )
            )
        if not findings:
            findings.append(
                FindingDraft(title="sqlmap completed", severity="info", description="Scan completed")
            )
        return ToolResult(findings=findings, raw=stdout)
