from __future__ import annotations

import httpx


class SpectreAgentClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    async def get_security_summary(self):
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{self.base_url}/api/security/summary")
                r.raise_for_status()
                return r.json()
            except Exception:
                return {}
