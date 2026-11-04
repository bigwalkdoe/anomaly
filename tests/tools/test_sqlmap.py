from __future__ import annotations

from anomaly_tools.sqlmap import SqlmapTool
from anomaly_tools.base import ToolSpec


def test_sqlmap_build_cmd_safe_defaults():
    tool = SqlmapTool()
    cmd = tool.build_cmd(ToolSpec(targets=["https://example.com/?id=1"]))
    assert cmd[0] == "sqlmap"
    assert "--batch" in cmd


def test_sqlmap_parse_finding():
    tool = SqlmapTool()
    res = tool.parse("sqlmap identified the following injection point")
    assert res.findings[0].severity == "high"
