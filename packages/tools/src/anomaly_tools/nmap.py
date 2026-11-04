from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec


class NmapTool:
    name = "nmap"
    supported_target_types = ["ip", "domain", "cidr"]

    def build_cmd(self, spec: ToolSpec) -> list[str]:
        cmd = ["nmap"]
        params = spec.params or {}
        scan_type = params.get("scan_type", "syn")
        if scan_type == "syn":
            cmd.append("-sS")
        elif scan_type == "connect":
            cmd.append("-sT")
        ports = params.get("ports")
        if ports:
            cmd.extend(["-p", str(ports)])
        top_ports = params.get("top_ports")
        if top_ports and not ports:
            cmd.extend(["--top-ports", str(top_ports)])
        timing = params.get("timing")
        if timing:
            cmd.append(f"-T{timing}")
        cmd.append("-oN")
        cmd.append("-")
        for t in spec.targets:
            cmd.append(t)
        return cmd

    def parse(self, stdout: str) -> ToolResult:
        findings = []
        for line in stdout.splitlines():
            line = line.strip()
            if "/tcp" in line and "open" in line:
                findings.append(
                    FindingDraft(
                        title=f"Open port: {line}",
                        severity="info",
                        description=line,
                    )
                )
        if not findings:
            findings.append(FindingDraft(title="nmap scan completed", severity="info", description="Scan completed"))
        return ToolResult(findings=findings, raw=stdout)
