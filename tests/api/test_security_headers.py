from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_security_headers_present(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in headers.get("content-security-policy", "")
