from .base import FindingDraft, Tool, ToolResult, ToolSpec
from .registry import ToolRegistry
from .stub import StubTool, stub_tool

__all__ = [
    "FindingDraft",
    "Tool",
    "ToolResult",
    "ToolSpec",
    "ToolRegistry",
    "stub_tool",
    "StubTool",
    "get_default_registry",
]


from .ffuf import FfufTool
from .httpx import HttpxTool
from .nmap import NmapTool
from .nuclei import NucleiTool
from .sqlmap import SqlmapTool


def get_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    for cls in [StubTool, NmapTool, HttpxTool, NucleiTool, FfufTool, SqlmapTool]:
        try:
            reg.register(cls())
        except Exception:
            pass
    return reg


__all__.extend(["NmapTool", "HttpxTool", "NucleiTool", "FfufTool", "SqlmapTool"])
