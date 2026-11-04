from __future__ import annotations

from fastapi import APIRouter

from anomaly_api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(db: DbSession):
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as e:
        return {"status": "degraded", "database": "error"}


@router.get("/api/version")
async def version():
    return {"version": "0.1.0"}


@router.get("/healthz")
async def healthz(db: DbSession):
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}
