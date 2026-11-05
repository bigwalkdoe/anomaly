from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from anomaly_tools.ffuf import parse_ffuf_json, run_ffuf
from anomaly_tools.generic import parse_passthrough, run_not_implemented
from anomaly_tools.nmap import parse_nmap_xml, run_nmap
from anomaly_tools.nuclei import parse_nuclei_output, run_nuclei
from anomaly_tools.recon import parse_recon_output, run_recon
from anomaly_tools.stub import ToolResult, run_stub

ParseFn = Callable[[str, str, int, list[str], dict[str, Any] | None], ToolResult]


@dataclass
class ToolDefinition:
    name: str
    image: str
    # If parse_output is set, executor uses runner stdout/stderr/exit_code.
    parse_output: Callable[..., ToolResult] | None = None
    # Fallback in-process executor (used by stub / tests).
    run_direct: Callable[..., Any] | None = None
    default_timeout_s: int = 300


def _stub_parse(
    stdout: str, stderr: str, exit_code: int, targets: list[str], params: dict[str, Any] | None
) -> ToolResult:
    # Stub returns findings via run_direct for compat; parsing stdout is a no-op fallback.
    return ToolResult(stdout=stdout, stderr=stderr, exit_code=exit_code, parsed_findings=[])


TOOL_DEFS: dict[str, ToolDefinition] = {
    "stub": ToolDefinition(name="stub", image="anomaly-runner:dev", run_direct=run_stub),
    "nmap": ToolDefinition(
        name="nmap",
        image="anomaly-tools-nmap:dev",
        parse_output=lambda stdout, stderr, exit_code, targets, params: parse_nmap_xml(
            stdout or "", targets, params
        ),
        run_direct=run_nmap,
    ),
    "nuclei": ToolDefinition(
        name="nuclei",
        image="anomaly-tools-nuclei:dev",
        parse_output=lambda stdout, stderr, exit_code, targets, params: parse_nuclei_output(
            stdout or "", targets, params
        ),
        run_direct=run_nuclei,
    ),
    "ffuf": ToolDefinition(
        name="ffuf",
        image="anomaly-tools-ffuf:dev",
        parse_output=lambda stdout, stderr, exit_code, targets, params: parse_ffuf_json(
            stdout or "", targets, params
        ),
        run_direct=run_ffuf,
    ),
    "sqlmap": ToolDefinition(
        "sqlmap", "anomaly-tools-sqlmap:dev", parse_passthrough, run_not_implemented
    ),
    "metasploit": ToolDefinition(
        "metasploit", "anomaly-tools-metasploit:dev", parse_passthrough, run_not_implemented
    ),
    "burp": ToolDefinition(
        "burp", "anomaly-tools-burp:dev", parse_passthrough, run_not_implemented
    ),
    "recon": ToolDefinition(
        name="recon",
        image="anomaly-tools-recon:dev",
        parse_output=lambda stdout, stderr, exit_code, targets, params: parse_recon_output(
            stdout or "", targets, params
        ),
        run_direct=run_recon,
    ),
    "httpx": ToolDefinition(
        name="httpx",
        image="anomaly-tools-recon:dev",
        parse_output=lambda stdout, stderr, exit_code, targets, params: parse_recon_output(
            stdout or "", targets, params
        ),
        run_direct=run_recon,
    ),
}

# Back-compat name used by executor/foundation code.
TOOL_REGISTRY = {k: (v.run_direct or run_stub) for k, v in TOOL_DEFS.items()}
