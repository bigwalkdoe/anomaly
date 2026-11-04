from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()
        self.clients[client] = [t for t in self.clients[client] if now - t < self.period]
        if len(self.clients[client]) >= self.calls:
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        self.clients[client].append(now)
        response = await call_next(request)
        return response
