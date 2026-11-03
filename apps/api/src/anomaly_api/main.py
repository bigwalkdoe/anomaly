from __future__ import annotations

from fastapi import FastAPI

from anomaly_api.routers import auth, health

app = FastAPI(title="Anomaly API", version="0.1.0")

app.include_router(health.router)
app.include_router(auth.router)
