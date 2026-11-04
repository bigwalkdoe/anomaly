from __future__ import annotations

from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec
from anomaly_tools.registry import ToolRegistry


def test_registry_register_and_get():
    class Dummy:
        name = "dummy"
        supported_target_types = ["domain"]

        def build_cmd(self, spec: ToolSpec):
            return ["echo", spec.targets[0] if spec.targets else ""]

        def parse(self, stdout: str):
            return ToolResult(findings=[FindingDraft(title="test")], raw=stdout)

    reg = ToolRegistry()
    tool = Dummy()
    reg.register(tool)
    assert reg.get("dummy") is tool
    assert "dummy" in reg.list_tools()
