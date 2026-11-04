from __future__ import annotations

from fastapi import APIRouter

from anomaly_api.deps import CurrentUser

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: CurrentUser):
    return []


@router.post("")
async def create_notification(payload: dict, user: CurrentUser):
    return {"id": "notif_1", "title": payload.get("title"), "read": False}
