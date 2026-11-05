from fastapi import FastAPI

from anomaly_api.routers import audit, auth, engagements, findings, runs

app = FastAPI(title="Anomaly API", version="0.1.0")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/version")
async def version() -> dict[str, str]:
    return {"version": "0.1.0"}


app.include_router(auth.router)
app.include_router(engagements.router)
app.include_router(findings.router)
app.include_router(runs.router)
app.include_router(audit.router)


