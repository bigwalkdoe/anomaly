from __future__ import annotations

from anomaly_tools import get_default_registry


def test_default_registry_has_tools():
    reg = get_default_registry()
    assert reg.get("nmap") is not None
    assert reg.get("nuclei") is not None
