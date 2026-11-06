from __future__ import annotations

import httpx


class SpectreSuiteClient:
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url

    async def query_prometheus(self, query: str):
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{self.base_url}/api/v1/query", params={"query": query})
                r.raise_for_status()
                return r.json()
            except Exception:
                return {}
