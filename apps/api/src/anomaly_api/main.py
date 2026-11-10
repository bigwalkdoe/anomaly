from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from anomaly_core.db import SessionLocal
from anomaly_core.rbac import ensure_default_rbac
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from anomaly_api.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    http_exception_handler,
    validation_exception_handler,
)
from anomaly_api.routers import (
    ai,
    api_keys,
    audit,
    auth,
    dashboard,
    engagements,
    evidence,
    findings,
    health,
    metrics,
    mfa,
    notifications,
    playbooks,
    reports,
    runs,
    schedules,
    search,
    stats,
    tags,
    upload,
    users,
    vulnerabilities,
    webhooks,
    ws,
)

tags_metadata = [
    {
        "name": "health",
        "description": "Health check and version endpoints for monitoring.",
    },
    {
        "name": "auth",
        "description": "Authentication: register, login, refresh, logout, token verification.",
    },
    {
        "name": "engagements",
        "description": "Engagement CRUD, scope management, and target assignment.",
    },
    {
        "name": "findings",
        "description": "Finding management: create, read, update, status transitions, delete.",
    },
    {
        "name": "runs",
        "description": "Tool run management: enqueue, status, logs, scope warnings.",
    },
    {
        "name": "audit",
        "description": "Immutable audit log: list, filter by engagement, access control.",
    },
    {
        "name": "users",
        "description": "User management and profile endpoints.",
    },
    {
        "name": "stats",
        "description": "Platform-wide statistics and metrics.",
    },
    {
        "name": "dashboard",
        "description": "Dashboard overview with engagement and severity summaries.",
    },
    {
        "name": "tags",
        "description": "Tag management for categorizing findings and engagements.",
    },
    {
        "name": "webhooks",
        "description": "Webhook subscription and delivery management.",
    },
    {
        "name": "websocket",
        "description": "Real-time WebSocket connections for run log streaming.",
    },
    {
        "name": "playbooks",
        "description": "Playbook CRUD: multi-step tool execution workflows.",
    },
    {
        "name": "upload",
        "description": "File upload to MinIO evidence store.",
    },
    {
        "name": "search",
        "description": "Full-text search across engagements and findings.",
    },
    {
        "name": "notifications",
        "description": "Notification center: list, create, mark as read.",
    },
    {
        "name": "vulnerabilities",
        "description": "Vulnerability summary and severity breakdowns.",
    },
    {
        "name": "ai",
        "description": "AI-assisted suggestions and drafting (advisory, audited).",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Seed default RBAC roles/permissions at startup (idempotent)."""
    async with SessionLocal() as session:
        await ensure_default_rbac(session)
    yield


app = FastAPI(
    title="Anomaly API",
    version="0.1.0",
    description=(
        "Anomaly - Penetration Testing and Cyber Operations Platform\n\n"
        "## Authentication\n"
        "Most endpoints require a Bearer JWT access token. Obtain one via `/api/auth/login`.\n"
        "Refresh tokens are rotated on use and can be revoked via `/api/auth/logout`.\n\n"
        "## Authorization\n"
        "Access is role-based (admin, pentester, client_viewer) and scoped per engagement.\n"
        "Cross-engagement access returns 404 to avoid enumeration.\n\n"
        "## Scope Enforcement\n"
        "Tool runs are checked against engagement scope before execution. Out-of-scope "
        "targets are logged with a warning and the run is marked with `scope_warning=true`.\n\n"
        "## Audit Trail\n"
        "All state-changing actions are recorded in an immutable audit log.\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
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
app.include_router(ws.router)
app.include_router(playbooks.router)
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(evidence.router)
app.include_router(api_keys.router)
app.include_router(metrics.router)
app.include_router(mfa.router)
app.include_router(schedules.router)
app.include_router(reports.router)
app.include_router(vulnerabilities.router)
app.include_router(ai.router)
