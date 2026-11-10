from __future__ import annotations

from collections.abc import Iterator, Mapping
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


class _LazyCompatRegistry:
    """Compat proxy: delegates to a cached default registry on first access.

    Avoids import-time side effects while ensuring legacy callers (e.g.
    ``TOOL_REGISTRY.get("nmap")``) resolve real tools.
    """

    def __init__(self) -> None:
        self._cached: ToolRegistry | None = None

    def _registry(self) -> ToolRegistry:
        if self._cached is None:
            self._cached = get_default_registry()
        return self._cached

    def get(self, name: str) -> Tool | None:
        return self._registry().get(name)

    def register(self, tool: Tool) -> None:
        self._registry().register(tool)

    def list_tools(self) -> list[str]:
        return self._registry().list_tools()


class _LazyCompatDefs(Mapping[str, Any]):
    """Compat mapping over tool names; lazy and consistent with TOOL_REGISTRY."""

    def __init__(self, registry: _LazyCompatRegistry) -> None:
        self._registry = registry

    def _data(self) -> dict[str, Tool | None]:
        return {name: self._registry.get(name) for name in self._registry.list_tools()}

    def __getitem__(self, key: str) -> Any:
        return self._data()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._registry.list_tools())

    def __len__(self) -> int:
        return len(self._registry.list_tools())

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self._registry.get(key) is not None

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        value = self._registry.get(key)
        return default if value is None else value

    def keys(self):  # type: ignore[override]
        return self._data().keys()

    def values(self):  # type: ignore[override]
        return self._data().values()

    def items(self):  # type: ignore[override]
        return self._data().items()


# Compat aliases for legacy callers; thin wrappers over the registry model.
# Materialized lazily on first access to avoid import-time side effects.
TOOL_REGISTRY: Any = _LazyCompatRegistry()
TOOL_DEFS: Any = _LazyCompatDefs(TOOL_REGISTRY)
