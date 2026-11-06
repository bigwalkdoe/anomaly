from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_still_accessible(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
