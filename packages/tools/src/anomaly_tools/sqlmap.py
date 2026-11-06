from __future__ import annotations

from typing import Any

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

    def parse(
        self, stdout: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
    ) -> ToolResult:
        findings = []
        low = (stdout or "").lower()
        if "sqlmap identified" in low or "vulnerable" in low:
            findings.append(
                FindingDraft(
                    title="SQL injection detected",
                    severity="high",
                    description=(stdout or "")[:500],
                )
            )
        if not findings:
            findings.append(
                FindingDraft(
                    title="sqlmap completed", severity="info", description="Scan completed"
                )
            )
        return ToolResult(findings=findings, raw=stdout or "", stdout=stdout or "", exit_code=0)


def parse_sqlmap_output(
    output: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    return SqlmapTool().parse(output, targets, params)


async def run_sqlmap(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    return ToolResult(stdout="", stderr="", exit_code=0, findings=[], parsed_findings=[])
