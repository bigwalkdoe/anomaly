from __future__ import annotations

from anomaly_tools import get_default_registry
from anomaly_tools.base import ToolSpec


def test_default_registry_has_core_tools():
    reg = get_default_registry()
    for name in ["stub", "nmap", "httpx", "nuclei", "ffuf", "sqlmap"]:
        assert reg.get(name) is not None, name


def test_registry_tools_build_and_parse_end_to_end():
    reg = get_default_registry()
    stub = reg.get("stub")
    assert stub is not None
    spec = ToolSpec(targets=["example.com"], params={})
    cmd = stub.build_cmd(spec)
    assert isinstance(cmd, list) and cmd
    parsed = stub.parse("stub reached example.com")
    assert parsed.findings
    assert any("reachable" in (f.title.lower() + f.description.lower()) for f in parsed.findings)

    nmap = reg.get("nmap")
    assert nmap is not None
    cmd = nmap.build_cmd(ToolSpec(targets=["example.com"]))
    assert cmd[0] == "nmap"
    parsed = nmap.parse("80/tcp open http")
    assert any("80/tcp" in f.title for f in parsed.findings)
