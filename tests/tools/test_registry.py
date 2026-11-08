from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec
from anomaly_tools.registry import ToolRegistry


class Dummy:
    name = "dummy"
    supported_target_types = ["domain"]

    def build_cmd(self, spec: ToolSpec):
        return ["echo", spec.targets[0] if spec.targets else ""]

    def parse(self, stdout: str):
        return ToolResult(findings=[FindingDraft(title="t")], raw=stdout, discovered_targets=[])


def test_registry_register_get_list():
    reg = ToolRegistry()
    d = Dummy()
    reg.register(d)
    assert reg.get("dummy") is d
    assert "dummy" in reg.list_tools()


def test_toolresult_has_discovered_targets():
    r = ToolResult(findings=[], discovered_targets=[{"value": "https://a.example", "type": "url"}])
    assert r.discovered_targets[0]["value"] == "https://a.example"


def test_legacy_tool_registry_compat_is_populated_on_access():
    # Legacy import pattern: compat surface must resolve real tools, not empty.
    from anomaly_tools import TOOL_REGISTRY

    tool = TOOL_REGISTRY.get("nmap")
    assert tool is not None
    assert getattr(tool, "name", None) == "nmap"
    assert "nmap" in TOOL_REGISTRY.list_tools()


def test_legacy_tool_registry_from_registry_module():
    from anomaly_tools.registry import TOOL_REGISTRY

    assert TOOL_REGISTRY.get("stub") is not None
    assert TOOL_REGISTRY.get("nope") is None


def test_legacy_tool_defs_consistent_with_registry():
    from anomaly_tools import TOOL_DEFS, TOOL_REGISTRY

    assert "nmap" in TOOL_DEFS
    assert TOOL_DEFS.get("nmap") is TOOL_REGISTRY.get("nmap")
    assert "nmap" in list(TOOL_DEFS.keys())
