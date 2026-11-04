from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/version")
async def version():
    return {"version": "0.1.0"}


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/api/config")
async def config():
    return {"features": ["runs", "findings", "ai", "tools"]}
