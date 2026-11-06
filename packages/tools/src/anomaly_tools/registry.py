from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from anomaly_tools.base import Tool
from anomaly_tools.stub import run_stub


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


# ---- Compat layer for feat/tool-packs-phase2 executor (TOOL_DEFS/ToolDefinition) ----

@dataclass
class ToolDefinition:
    name: str
    image: str
    parse_output: Callable[..., Any] | None = None
    run_direct: Callable[..., Any] | None = None
    default_timeout_s: int = 300


def _wrap_parse(fn: Callable[..., Any]) -> Callable[..., Any]:
    def _p(stdout: str, stderr: str, exit_code: int, targets: list[str], params: dict[str, Any] | None):
        try:
            return fn(stdout or "", targets, params)
        except TypeError:
            return fn(stdout or "")
    return _p


def _build_tool_defs() -> dict[str, ToolDefinition]:
    defs: dict[str, ToolDefinition] = {
        "stub": ToolDefinition(name="stub", image="anomaly-runner:dev", run_direct=run_stub),
    }
    # Optional tools - wired fully in Task 2; keep placeholders/imports resilient.
    try:
        from anomaly_tools.nmap import parse_nmap_xml, run_nmap

        defs["nmap"] = ToolDefinition(
            name="nmap",
            image="anomaly-tools-nmap:dev",
            parse_output=_wrap_parse(parse_nmap_xml),
            run_direct=run_nmap,
        )
    except Exception:
        pass
    try:
        from anomaly_tools.nuclei import parse_nuclei_output, run_nuclei

        defs["nuclei"] = ToolDefinition(
            name="nuclei",
            image="anomaly-tools-nuclei:dev",
            parse_output=_wrap_parse(parse_nuclei_output),
            run_direct=run_nuclei,
        )
    except Exception:
        pass
    try:
        from anomaly_tools.ffuf import parse_ffuf_json, run_ffuf

        defs["ffuf"] = ToolDefinition(
            name="ffuf",
            image="anomaly-tools-ffuf:dev",
            parse_output=_wrap_parse(parse_ffuf_json),
            run_direct=run_ffuf,
        )
    except Exception:
        pass
    try:
        from anomaly_tools.recon import parse_recon_output, run_recon

        defs["recon"] = ToolDefinition(
            name="recon",
            image="anomaly-tools-recon:dev",
            parse_output=_wrap_parse(parse_recon_output),
            run_direct=run_recon,
        )
        defs["httpx"] = ToolDefinition(
            name="httpx",
            image="anomaly-tools-recon:dev",
            parse_output=_wrap_parse(parse_recon_output),
            run_direct=run_recon,
        )
    except Exception:
        pass
    try:
        from anomaly_tools.generic import parse_passthrough, run_not_implemented

        for name, image in [
            ("sqlmap", "anomaly-tools-sqlmap:dev"),
            ("metasploit", "anomaly-tools-metasploit:dev"),
            ("burp", "anomaly-tools-burp:dev"),
        ]:
            defs.setdefault(
                name,
                ToolDefinition(name, image, parse_passthrough, run_not_implemented),
            )
    except Exception:
        pass
    # If sqlmap tool class exists, prefer it (Task 2)
    try:
        from anomaly_tools.sqlmap import SqlmapTool

        st = SqlmapTool()

        def _sqlmap_parse(stdout, stderr, exit_code, targets, params):
            return st.parse(stdout or "")

        defs["sqlmap"] = ToolDefinition(
            name="sqlmap",
            image="anomaly-tools-sqlmap:dev",
            parse_output=_sqlmap_parse,
            run_direct=None,
        )
    except Exception:
        pass
    return defs


TOOL_DEFS: dict[str, ToolDefinition] = _build_tool_defs()

# Back-compat name used by some code.
TOOL_REGISTRY = {k: (v.run_direct or run_stub) for k, v in TOOL_DEFS.items()}


def get_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    from anomaly_tools.stub import StubTool

    reg.register(StubTool())
    for cls_path in [
        ("anomaly_tools.nmap", "NmapTool"),
        ("anomaly_tools.httpx", "HttpxTool"),
        ("anomaly_tools.recon", "ReconTool"),
        ("anomaly_tools.nuclei", "NucleiTool"),
        ("anomaly_tools.ffuf", "FfufTool"),
        ("anomaly_tools.sqlmap", "SqlmapTool"),
    ]:
        try:
            mod = __import__(cls_path[0], fromlist=[cls_path[1]])
            cls = getattr(mod, cls_path[1])
            reg.register(cls())
        except Exception:
            pass
    # aliases: ensure httpx/recon both present if one registered
    if reg.get("recon") and not reg.get("httpx"):
        reg._tools["httpx"] = reg.get("recon")  # type: ignore[assignment]
    if reg.get("httpx") and not reg.get("recon"):
        reg._tools["recon"] = reg.get("httpx")  # type: ignore[assignment]
    return reg
