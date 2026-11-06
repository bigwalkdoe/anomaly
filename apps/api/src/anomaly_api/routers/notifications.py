from __future__ import annotations

from anomaly_core.models import RoleName
from anomaly_core.rbac import has_role
from fastapi import APIRouter, HTTPException

from anomaly_api.deps import CurrentUser

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: CurrentUser):
    return []


@router.post("")
async def create_notification(payload: dict, user: CurrentUser):
    return {"id": "notif_1", "title": payload.get("title"), "read": False}


@router.post("/broadcast")
async def broadcast_notification(
    payload: dict,
    user: CurrentUser,
):
    """Broadcast a notification to all connected WebSocket clients (admin only)."""
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Only admins can broadcast notifications")

    from anomaly_api.routers.ws import notification_manager

    message = {
        "type": "notification",
        "title": payload.get("title", "Notification"),
        "message": payload.get("message", ""),
        "severity": payload.get("severity", "info"),
    }

    await notification_manager.broadcast_to_all(message)

    return {"broadcast": True, "recipients": len(notification_manager.active_connections)}
