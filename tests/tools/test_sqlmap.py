from anomaly_tools.base import ToolSpec
from anomaly_tools.sqlmap import SqlmapTool


def test_sqlmap_build_cmd_safe_defaults():
    tool = SqlmapTool()
    cmd = tool.build_cmd(ToolSpec(targets=["https://example.com/?id=1"]))
    assert cmd[0] == "sqlmap"
    assert "--batch" in cmd
    assert "--banner" in cmd


def test_sqlmap_risky_options_require_explicit_flag():
    tool = SqlmapTool()
    cmd = tool.build_cmd(
        ToolSpec(targets=["https://example.com/?id=1"], params={"level": 5, "risk": 3})
    )
    assert "--level" not in cmd
    assert "--risk" not in cmd
    cmd = tool.build_cmd(
        ToolSpec(
            targets=["https://example.com/?id=1"],
            params={"level": 5, "risk": 3, "allow_risky_options": True},
        )
    )
    assert "--level" in cmd and "5" in cmd
    assert "--risk" in cmd and "3" in cmd


def test_sqlmap_parse_finding():
    tool = SqlmapTool()
    res = tool.parse("sqlmap identified the following injection point")
    assert res.findings[0].severity == "high"
