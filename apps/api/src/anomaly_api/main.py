from __future__ import annotations

from fastapi import FastAPI

from anomaly_api.routers import audit, auth, engagements, findings, health, runs

app = FastAPI(title="Anomaly API", version="0.1.0")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(engagements.router)
app.include_router(findings.router)
app.include_router(runs.router)
app.include_router(audit.router)
