from __future__ import annotations

import pytest

from anomaly_ai import AIService, get_provider
from anomaly_ai.providers import AIMessage, AnthropicProvider, OllamaProvider, OpenAIProvider


class DummyResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._data


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers or {}})
        # default response filled by tests via attribute
        return self.response


@pytest.mark.asyncio
async def test_get_provider_defaults_from_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "miniosecret")
    # clear cached settings if any
    import anomaly_core.config as cfg
    cfg._settings = None

    p = get_provider()
    assert p.name == "ollama"
    assert getattr(p, "model", None) == "llama3.1"


@pytest.mark.asyncio
async def test_ollama_provider_complete(monkeypatch):
    dummy = DummyClient()
    dummy.response = DummyResponse(
        {"message": {"content": "hello"}, "prompt_eval_count": 3, "eval_count": 5}
    )
    monkeypatch.setattr("anomaly_ai.providers.httpx.AsyncClient", lambda *a, **k: dummy)

    p = OllamaProvider(base_url="http://ollama:11434", model="llama3.1")
    resp = await p.complete([AIMessage(role="user", content="hi")])

    assert resp.content == "hello"
    assert resp.model == "llama3.1"
    assert dummy.calls[0]["url"] == "http://ollama:11434/api/chat"
    assert dummy.calls[0]["json"]["stream"] is False
    assert dummy.calls[0]["json"]["messages"][0]["content"] == "hi"


@pytest.mark.asyncio
async def test_openai_provider_complete(monkeypatch):
    dummy = DummyClient()
    dummy.response = DummyResponse(
        {"choices": [{"message": {"content": "openai hi"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}}
    )
    monkeypatch.setattr("anomaly_ai.providers.httpx.AsyncClient", lambda *a, **k: dummy)

    p = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini", base_url="https://api.openai.com/v1")
    resp = await p.complete([AIMessage(role="user", content="hi")])

    assert resp.content == "openai hi"
    assert dummy.calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert dummy.calls[0]["headers"].get("Authorization") == "Bearer sk-test"
    assert dummy.calls[0]["json"]["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_anthropic_provider_complete(monkeypatch):
    dummy = DummyClient()
    dummy.response = DummyResponse(
        {"content": [{"type": "text", "text": "anthropic hi"}], "usage": {"input_tokens": 1, "output_tokens": 2}}
    )
    monkeypatch.setattr("anomaly_ai.providers.httpx.AsyncClient", lambda *a, **k: dummy)

    p = AnthropicProvider(api_key="ak-test", model="claude-3-5-sonnet", base_url="https://api.anthropic.com/v1")
    resp = await p.complete([AIMessage(role="user", content="hi")])

    assert resp.content == "anthropic hi"
    assert dummy.calls[0]["url"] == "https://api.anthropic.com/v1/messages"
    assert dummy.calls[0]["headers"].get("x-api-key") == "ak-test"
    assert "anthropic-version" in dummy.calls[0]["headers"]
    assert dummy.calls[0]["json"]["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_ai_service_complete_still_works_with_mock_provider():
    # Preserve basic service behavior; provider is injected
    dummy = DummyClient()
    dummy.response = DummyResponse({"message": {"content": "svc"}, "prompt_eval_count": 1, "eval_count": 1})

    class P(OllamaProvider):
        async def complete(self, messages, **kwargs):
            return await super().complete(messages, **kwargs)

    import anomaly_ai.providers as providers
    # monkeypatch not available here; use simple fake provider
    class Fake:
        name = "fake"
        model = "m"
        async def complete(self, messages, **kwargs):
            from anomaly_ai.providers import AIResponse
            return AIResponse(content="ok", model="m", usage={"prompt_tokens": 1, "completion_tokens": 1})

    svc = AIService(provider=Fake())
    resp = await svc.complete([AIMessage(role="user", content="test")])
    assert resp.content == "ok"

import json
from types import SimpleNamespace


class CapturingProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, content: str):
        self.content = content
        self.calls = []

    async def complete(self, messages, **kwargs):
        self.calls.append(messages)
        from anomaly_ai.providers import AIResponse
        return AIResponse(content=self.content, model=self.model, usage={"prompt_tokens": 1, "completion_tokens": 2})


@pytest.mark.asyncio
async def test_suggest_tools_parses_structured_json():
    payload = {
        "suggestions": [
            {"tool": "nmap", "reason": "port scan", "targets_hint": "10.0.0.1", "params": {"top_ports": 100}, "priority": "high"}
        ],
        "notes": "start here",
    }
    provider = CapturingProvider("```json\n" + json.dumps(payload) + "\n```")
    svc = AIService(provider=provider)
    result = await svc.suggest_tools("scan the host", context={"target": "10.0.0.1"})

    assert result["parse_success"] is True
    assert result["raw"] is None
    assert result["notes"] == "start here"
    assert result["suggestions"][0]["tool"] == "nmap"
    assert result["provider"] == "fake"
    assert result["model"] == "fake-model"
    # prompt should include objective and some known tool names
    sent = "\n".join(m.content for m in provider.calls[0])
    assert "scan the host" in sent
    assert "nmap" in sent


@pytest.mark.asyncio
async def test_suggest_tools_falls_back_on_invalid_json():
    provider = CapturingProvider("I suggest using nmap first.")
    svc = AIService(provider=provider)
    result = await svc.suggest_tools("scan the host")

    assert result["parse_success"] is False
    assert result["suggestions"] == []
    assert result["raw"] == "I suggest using nmap first."


@pytest.mark.asyncio
async def test_suggest_tools_logs_audit(monkeypatch):
    payload = {"suggestions": [{"tool": "nmap", "reason": "scan"}], "notes": ""}
    provider = CapturingProvider(json.dumps(payload))
    logs = []

    async def fake_log(*, actor_id, action, resource_type, resource_id, engagement_id, metadata, db):
        logs.append({
            "actor_id": actor_id, "action": action, "resource_type": resource_type,
            "resource_id": resource_id, "engagement_id": engagement_id, "metadata": metadata, "db": db,
        })

    monkeypatch.setattr("anomaly_ai.service.AuditService.log", fake_log)
    svc = AIService(provider=provider, db=object())
    result = await svc.suggest_tools("scan", actor_id="u1", engagement_id="e1")

    assert result["parse_success"] is True
    assert logs, "expected audit log call"
    assert logs[-1]["action"] == "ai.suggest_tools"
    md = logs[-1]["metadata"]
    assert md["provider"] == "fake"
    assert md["model"] == "fake-model"
    assert md["parse_success"] is True
    assert md["suggestion_count"] == 1
