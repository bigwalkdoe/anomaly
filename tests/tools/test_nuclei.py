from __future__ import annotations

from anomaly_tools.base import ToolSpec
from anomaly_tools.nuclei import NucleiTool


def test_nuclei_build_cmd():
    tool = NucleiTool()
    cmd = tool.build_cmd(ToolSpec(targets=["example.com"], params={"severity": "high"}))
    assert cmd[0] == "nuclei"
    assert "-severity" in cmd


def test_nuclei_parse():
    tool = NucleiTool()
    res = tool.parse('{"template-id":"test"}')
    assert len(res.findings) >= 1
