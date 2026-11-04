from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from anomaly_core.db import SessionLocal
from anomaly_core.rbac import ensure_default_rbac

from anomaly_api.middleware import http_exception_handler, validation_exception_handler

from anomaly_api.middleware import RateLimitMiddleware, RequestIDMiddleware
from anomaly_api.routers import audit, auth, dashboard, engagements, findings, health, notifications, runs, search, stats, tags, upload, users, webhooks


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Seed default RBAC roles/permissions at startup (idempotent)."""
    async with SessionLocal() as session:
        await ensure_default_rbac(session)
    yield


app = FastAPI(
    title="Anomaly API",
    version="0.1.0",
    description="Anomaly - Penetration Testing and Cyber Operations Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_middleware(RateLimitMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(engagements.router)
app.include_router(findings.router)
app.include_router(runs.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(dashboard.router)
app.include_router(tags.router)
app.include_router(webhooks.router)
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(search.router)
app.include_router(notifications.router)
