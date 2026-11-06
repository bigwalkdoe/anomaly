from __future__ import annotations

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
