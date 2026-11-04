from __future__ import annotations

import pytest

from anomaly_ai import AIService, get_provider
from anomaly_ai.providers import AIMessage


@pytest.mark.asyncio
async def test_get_provider_defaults():
    p = get_provider()
    assert p.name == "ollama"


@pytest.mark.asyncio
async def test_ai_service_complete():
    svc = AIService(provider=get_provider("openai"))
    resp = await svc.complete([AIMessage(role="user", content="test")])
    assert "OpenAI" in resp.content
    assert resp.model


@pytest.mark.asyncio
async def test_draft_finding_and_report():
    svc = AIService()
    f = await svc.draft_finding("nmap found port 80 open")
    r = await svc.draft_report("1 finding")
    assert f.content
    assert r.content
