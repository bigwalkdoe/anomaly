from __future__ import annotations

from anomaly_tools.nmap import NmapTool
from anomaly_tools.base import ToolSpec


def test_nmap_build_cmd_defaults():
    tool = NmapTool()
    spec = ToolSpec(targets=["example.com"])
    cmd = tool.build_cmd(spec)
    assert cmd[0] == "nmap"
    assert "-sS" in cmd
    assert "example.com" in cmd


def test_nmap_parse_open_ports():
    tool = NmapTool()
    out = "80/tcp open http\n22/tcp open ssh\n"
    res = tool.parse(out)
    assert len(res.findings) >= 2
