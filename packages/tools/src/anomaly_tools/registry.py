from __future__ import annotations

from typing import Any

from anomaly_tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


def get_default_registry() -> ToolRegistry:
    """Return a populated registry. Canonical factory for tool resolution."""
    # Local imports avoid import cycles and keep registry lightweight to import.
    from anomaly_tools.ffuf import FfufTool
    from anomaly_tools.httpx import HttpxTool
    from anomaly_tools.nmap import NmapTool
    from anomaly_tools.nuclei import NucleiTool
    from anomaly_tools.recon import ReconTool
    from anomaly_tools.sqlmap import SqlmapTool
    from anomaly_tools.stub import StubTool

    reg = ToolRegistry()
    for tool in [
        StubTool(),
        NmapTool(),
        HttpxTool(),
        ReconTool(),
        NucleiTool(),
        FfufTool(),
        SqlmapTool(),
    ]:
        reg.register(tool)
    return reg


# Compat aliases for legacy callers; thin wrappers over the registry model.
# TOOL_REGISTRY is intentionally left unpopulated to avoid side effects on import;
# use get_default_registry() for a populated registry.
TOOL_REGISTRY = ToolRegistry()
TOOL_DEFS: dict[str, Any] = {}
