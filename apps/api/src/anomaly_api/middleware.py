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


from fastapi.middleware.cors import CORSMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import uuid

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})


async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "error": "Validation Error", "detail": exc.errors()})
