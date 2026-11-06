from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace
from typing import Any

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
        # Try XML first (nmap -oX)
        try:
            root = ET.fromstring(stdout)
        except Exception:
            root = None
        if root is not None and root.tag in ("nmaprun", "nmap", "scan"):
            findings = []
            for host in root.findall("host"):
                status = host.find("status")
                if status is not None and status.get("state") != "up":
                    continue
                addr_el = host.find("address[@addrtype='ipv4']")
                if addr_el is None:
                    addr_el = host.find("address")
                addr = addr_el.get("addr") if addr_el is not None else "unknown"
                ports = host.find("ports")
                if ports is None:
                    continue
                for port in ports.findall("port"):
                    st = port.find("state")
                    if st is None or st.get("state") != "open":
                        continue
                    portid = port.get("portid", "?")
                    proto = port.get("protocol", "tcp")
                    service = port.find("service")
                    svc_name = service.get("name", "") if service is not None else ""
                    title = f"Open {proto}/{portid} {svc_name} on {addr}".strip()
                    findings.append(
                        FindingDraft(
                            title=title,
                            severity="info",
                            description=f"Service: {svc_name or 'unknown'}",
                            metadata={"fingerprint": f"nmap:{addr}:{proto}:{portid}:{svc_name}"},
                        )
                    )
            if not findings:
                findings.append(
                    FindingDraft(
                        title="nmap scan completed", severity="info", description="Scan completed"
                    )
                )
            return ToolResult(findings=findings, raw=stdout)

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
            findings.append(
                FindingDraft(
                    title="nmap scan completed", severity="info", description="Scan completed"
                )
            )
        return ToolResult(findings=findings, raw=stdout)


def parse_nmap_xml(
    xml_text: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> SimpleNamespace:
    findings: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return SimpleNamespace(
            stdout=xml_text,
            stderr=str(exc),
            exit_code=1,
            parsed_findings=[],
            raw=xml_text,
            findings=[],
            discovered_targets=[],
        )
    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.get("state") != "up":
            continue
        addr_el = host.find("address[@addrtype='ipv4']")
        if addr_el is None:
            addr_el = host.find("address")
        addr = (
            addr_el.get("addr") if addr_el is not None else (targets[0] if targets else "unknown")
        )
        ports = host.find("ports")
        if ports is None:
            continue
        for port in ports.findall("port"):
            state = port.find("state")
            if state is None or state.get("state") != "open":
                continue
            portid = port.get("portid", "?")
            proto = port.get("protocol", "tcp")
            service = port.find("service")
            svc_name = service.get("name", "") if service is not None else ""
            product = service.get("product", "") if service is not None else ""
            version = service.get("version", "") if service is not None else ""
            detail = " ".join(x for x in [product, version] if x).strip()
            title = f"Open {proto}/{portid} {svc_name} on {addr}".strip()
            desc = f"Service: {svc_name or 'unknown'}"
            if detail:
                desc += f" ({detail})"
            findings.append(
                {
                    "title": title,
                    "severity": "info",
                    "description": desc,
                    "fingerprint": f"nmap:{addr}:{proto}:{portid}:{svc_name}",
                    "metadata": {
                        "host": addr,
                        "port": portid,
                        "protocol": proto,
                        "service": svc_name,
                    },
                }
            )
    return SimpleNamespace(
        stdout=xml_text,
        stderr="",
        exit_code=0,
        parsed_findings=findings,
        raw=xml_text,
        findings=[],
        discovered_targets=[],
    )
