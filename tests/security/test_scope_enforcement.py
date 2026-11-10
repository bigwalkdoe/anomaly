from __future__ import annotations

import pytest
from anomaly_core.scope import check_scope


def test_scope_denies_resolved_private_and_unlisted_targets():
    """Review Focus #2: scope enforcement must reject clearly out-of-scope destinations."""
    class ScopeObj:
        entries = []
    class Eng:
        scope = ScopeObj()
    eng = Eng()
    # with explicit in-scope entries, unlisted targets must be denied
    class Entry:
        def __init__(self, kind, value):
            self.kind = kind
            self.target_value = value
    eng.scope.entries = [Entry("in", "example.com")]
    res = check_scope(eng, ["evil.com", "127.0.0.1"])
    assert "evil.com" in [t.lower() for t in res.out_of_scope]
    assert res.has_warning is True
