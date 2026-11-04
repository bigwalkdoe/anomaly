from __future__ import annotations

from fastapi import APIRouter

from anomaly_api.deps import CurrentUser

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("")
async def list_webhooks(user: CurrentUser):
    return []


@router.post("")
async def create_webhook(payload: dict, user: CurrentUser):
    return {"id": "wh_1", "url": payload.get("url"), "active": True}
