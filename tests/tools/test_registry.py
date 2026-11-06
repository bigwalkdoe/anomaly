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
