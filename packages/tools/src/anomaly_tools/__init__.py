import contextlib
from typing import cast

from .base import FindingDraft, Tool, ToolResult, ToolSpec
from .ffuf import FfufTool
from .httpx import HttpxTool
from .nmap import NmapTool
from .nuclei import NucleiTool
from .registry import ToolRegistry
from .sqlmap import SqlmapTool
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


def get_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    for cls in [StubTool, NmapTool, HttpxTool, NucleiTool, FfufTool, SqlmapTool]:
        with contextlib.suppress(Exception):
            reg.register(cast(Tool, cls()))
    return reg


__all__.extend(["NmapTool", "HttpxTool", "NucleiTool", "FfufTool", "SqlmapTool"])
