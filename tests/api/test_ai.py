from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import Engagement, EngagementMode, Role, RoleName, User
from sqlalchemy import select


async def _make_admin(db_session):
    admin_role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if admin_role is None:
        admin_role = Role(name=RoleName.admin, description="admin")
        db_session.add(admin_role)
        await db_session.flush()
    user = User(
        email="admin-ai@example.com",
        name="Admin",
        password_hash=hash_password("pass"),
        roles=[admin_role],
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_ai_suggest_tools_requires_auth(client):
    resp = await client.post("/api/ai/suggest-tools", json={"objective": "scan web app"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_ai_suggest_tools_returns_structured(client, db_session, monkeypatch):
    admin = await _make_admin(db_session)
    await db_session.commit()
    token = create_access_token(admin.id, ["admin"])

    async def fake_suggest(
        self, objective, context=None, actor_id=None, engagement_id=None, **kwargs
    ):
        return {
            "provider": "fake",
            "model": "fake-model",
            "suggestions": [
                {
                    "tool": "nmap",
                    "reason": "scan ports",
                    "targets_hint": "",
                    "params": {},
                    "priority": "high",
                }
            ],
            "notes": "ok",
            "raw": None,
            "parse_success": True,
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }

    monkeypatch.setattr("anomaly_api.routers.ai.AIService.suggest_tools", fake_suggest)

    resp = await client.post(
        "/api/ai/suggest-tools",
        headers={"Authorization": f"Bearer {token}"},
        json={"objective": "scan web app"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["parse_success"] is True
    assert body["suggestions"][0]["tool"] == "nmap"
    assert body["provider"] == "fake"


@pytest.mark.asyncio
async def test_ai_suggest_tools_fallback(client, db_session, monkeypatch):
    admin = await _make_admin(db_session)
    await db_session.commit()
    token = create_access_token(admin.id, ["admin"])

    async def fake_suggest(
        self, objective, context=None, actor_id=None, engagement_id=None, **kwargs
    ):
        return {
            "provider": "fake",
            "model": "fake-model",
            "suggestions": [],
            "notes": None,
            "raw": "not json",
            "parse_success": False,
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }

    monkeypatch.setattr("anomaly_api.routers.ai.AIService.suggest_tools", fake_suggest)

    resp = await client.post(
        "/api/ai/suggest-tools",
        headers={"Authorization": f"Bearer {token}"},
        json={"objective": "scan web app"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["parse_success"] is False
    assert body["raw"] == "not json"


@pytest.mark.asyncio
async def test_ai_suggest_tools_engagement_access_enforced(client, db_session, monkeypatch):
    # user without access to engagement
    user_role = await db_session.scalar(select(Role).where(Role.name == RoleName.pentester))
    if user_role is None:
        user_role = Role(name=RoleName.pentester, description="pentester")
        db_session.add(user_role)
        await db_session.flush()
    owner = User(
        email="owner2@example.com",
        name="Owner",
        password_hash=hash_password("pass"),
        roles=[user_role],
    )
    other = User(
        email="other2@example.com",
        name="Other",
        password_hash=hash_password("pass"),
        roles=[user_role],
    )
    db_session.add_all([owner, other])
    await db_session.flush()
    eng = Engagement(name="E-ai", mode=EngagementMode.own_infra, owner_id=owner.id)
    db_session.add(eng)
    await db_session.commit()

    token = create_access_token(other.id, ["pentester"])
    resp = await client.post(
        "/api/ai/suggest-tools",
        headers={"Authorization": f"Bearer {token}"},
        json={"objective": "scan", "engagement_id": str(eng.id)},
    )
    assert resp.status_code in (403, 404)
