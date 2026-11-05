from anomaly_core.models.engagement import ScopeEntry
from anomaly_core.scope import check_scope


def test_in_scope_returns_no_warning():
    entries = [ScopeEntry(kind="in", target_value="example.com")]
    result = check_scope(entries, ["example.com"])
    assert result.has_warning is False
    assert result.in_scope == ["example.com"]
    assert result.out_of_scope == []


def test_out_of_scope_returns_warning():
    entries = [ScopeEntry(kind="in", target_value="example.com")]
    result = check_scope(entries, ["evil.com"])
    assert result.has_warning is True
    assert "evil.com" in result.out_of_scope


def test_mixed_returns_both_lists():
    entries = [
        ScopeEntry(kind="in", target_value="example.com"),
        ScopeEntry(kind="out", target_value="bad.example.com"),
    ]
    result = check_scope(entries, ["example.com", "bad.example.com", "other.com"])
    assert "example.com" in result.in_scope
    assert "bad.example.com" in result.out_of_scope
    assert "other.com" in result.out_of_scope
    assert result.has_warning is True
