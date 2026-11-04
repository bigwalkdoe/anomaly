from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anomaly_api.middleware import RateLimitMiddleware, RequestIDMiddleware
from anomaly_api.routers import audit, auth, engagements, findings, health, runs, stats, tags, users, webhooks

app = FastAPI(title="Anomaly API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(engagements.router)
app.include_router(findings.router)
app.include_router(runs.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(tags.router)
app.include_router(webhooks.router)
