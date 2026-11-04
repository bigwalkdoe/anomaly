from __future__ import annotations

from anomaly_tools.ffuf import FfufTool
from anomaly_tools.base import ToolSpec


def test_ffuf_build_cmd():
    tool = FfufTool()
    cmd = tool.build_cmd(ToolSpec(targets=["https://example.com/FUZZ"]))
    assert cmd[0] == "ffuf"


def test_ffuf_parse():
    tool = FfufTool()
    res = tool.parse("/admin [Status: 200]")
    assert len(res.findings) == 1
