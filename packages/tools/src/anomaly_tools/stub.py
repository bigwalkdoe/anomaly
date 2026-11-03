from __future__ import annotations


class ToolResult:
    def __init__(self, findings=None):
        self.findings = findings or []


def stub_tool(targets=None, **kwargs):
    targets = targets or []
    findings = []
    for t in targets:
        findings.append(
            {
                "title": "Stub finding: target reachable",
                "severity": "info",
                "description": f"Stub finding for {t}",
            }
        )
    if not findings:
        findings.append(
            {
                "title": "Stub finding: target reachable",
                "severity": "info",
                "description": "Stub finding",
            }
        )
    return ToolResult(findings=findings)
