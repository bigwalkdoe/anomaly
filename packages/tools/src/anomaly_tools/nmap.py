from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from anomaly_tools.stub import ToolResult


def parse_nmap_xml(
    xml_text: str, targets: list[str] | None = None, params: dict[str, Any] | None = None
) -> ToolResult:
    findings: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return ToolResult(stdout=xml_text, stderr=str(exc), exit_code=1, parsed_findings=[])

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
    return ToolResult(stdout=xml_text, exit_code=0, parsed_findings=findings)


async def run_nmap(targets: list[str], params: dict[str, Any] | None = None) -> ToolResult:
    # In-process placeholder; real execution happens in container via runner + parse_nmap_xml.
    return ToolResult(stdout="", exit_code=0, parsed_findings=[])
