from __future__ import annotations

import pytest

from anomaly_integrations import SpectreAgentClient, SpectreSuiteClient


@pytest.mark.asyncio
async def test_spectre_agent_client():
    c = SpectreAgentClient()
    res = await c.get_security_summary()
    assert isinstance(res, dict)


@pytest.mark.asyncio
async def test_spectre_suite_client():
    c = SpectreSuiteClient()
    res = await c.query_prometheus("up")
    assert isinstance(res, dict)
