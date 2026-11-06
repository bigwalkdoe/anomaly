from __future__ import annotations

from anomaly_tools.base import ToolSpec
from anomaly_tools.httpx import HttpxTool


def test_httpx_build_cmd():
    tool = HttpxTool()
    cmd = tool.build_cmd(ToolSpec(targets=["example.com"]))
    assert cmd[0] == "httpx"


def test_httpx_parse():
    tool = HttpxTool()
    res = tool.parse("https://example.com [200] Example")
    assert len(res.findings) == 1
