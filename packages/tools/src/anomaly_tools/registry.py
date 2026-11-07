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


# Compat aliases for legacy callers; thin wrappers over the registry model.
TOOL_REGISTRY = ToolRegistry()
TOOL_DEFS: dict[str, Any] = {}
