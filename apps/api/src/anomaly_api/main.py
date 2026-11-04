from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from anomaly_api.middleware import http_exception_handler, validation_exception_handler

from anomaly_api.middleware import RateLimitMiddleware, RequestIDMiddleware
from anomaly_api.routers import audit, auth, dashboard, engagements, findings, health, runs, search, stats, tags, upload, users, webhooks

app = FastAPI(
    title="Anomaly API",
    version="0.1.0",
    description="Anomaly - Penetration Testing and Cyber Operations Platform",
    docs_url="/docs",
    redoc_url="/redoc",
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
app.include_router(search.router)
