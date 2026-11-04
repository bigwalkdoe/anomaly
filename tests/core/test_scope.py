from __future__ import annotations

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models import Engagement, EngagementMode, Scope, ScopeEntry, ScopeEntryKind, User
from anomaly_core.scope import check_scope, parse_cidr


@pytest.mark.asyncio
async def test_in_scope_target_returns_no_warning(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    entry = ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    db_session.add(entry)
    await db_session.commit()

    # Reload to load relationships
    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["example.com"])
    assert result.has_warning is False
    assert result.out_of_scope == []


@pytest.mark.asyncio
async def test_out_of_scope_target_returns_warning(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    entry = ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    db_session.add(entry)
    await db_session.commit()

    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["evil.com"], scope_entries=[entry])
    assert result.has_warning is True
    assert "evil.com" in result.out_of_scope


@pytest.mark.asyncio
async def test_mixed_returns_both_lists(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    entry = ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    db_session.add(entry)
    await db_session.commit()

    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["example.com", "evil.com"], scope_entries=[entry])
    assert result.in_scope == ["example.com"]
    assert "evil.com" in result.out_of_scope
    assert result.has_warning is True


@pytest.mark.asyncio
async def test_out_of_scope_takes_precedence_over_in_scope(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="example.com")
    )
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.out, target_value="example.com")
    )
    await db_session.commit()

    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["example.com"])
    assert result.has_warning is True
    assert "example.com" in result.out_of_scope
    assert result.in_scope == []


@pytest.mark.asyncio
async def test_cidr_target_within_scope_entry_is_in_scope(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="10.0.0.0/8")
    )
    await db_session.commit()

    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["10.42.1.5"])
    assert result.has_warning is False
    assert result.in_scope == ["10.42.1.5"]


@pytest.mark.asyncio
async def test_cidr_target_outside_scope_entry_is_out_of_scope(db_session):
    user = User(email="u@example.com", name="U", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    eng = Engagement(name="E", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(
        ScopeEntry(scope_id=scope.id, kind=ScopeEntryKind.in_, target_value="10.0.0.0/8")
    )
    await db_session.commit()

    await db_session.refresh(eng)
    await db_session.refresh(scope)
    result = check_scope(eng, ["172.16.0.1"])
    assert result.has_warning is True
    assert "172.16.0.1" in result.out_of_scope


def test_parse_cidr_returns_network():
    net = parse_cidr("192.168.0.0/16")
    assert net is not None
    assert str(net) == "192.168.0.0/16"


def test_parse_cidr_invalid_returns_none():
    assert parse_cidr("not-a-cidr") is None
