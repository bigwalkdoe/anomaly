from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/version")
async def version() -> dict[str, str]:
    return {"name": "anomaly", "version": "0.1.0"}
