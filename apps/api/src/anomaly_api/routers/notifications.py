from __future__ import annotations

from anomaly_core.models import Membership, RoleName
from anomaly_core.rbac import has_role
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

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
    db: DbSession,
):
    """Broadcast a notification to connected WebSocket clients in the admin's tenant scope."""
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Only admins can broadcast notifications")

    from anomaly_api.routers.ws import notification_manager

    org_rows = (
        await db.scalars(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )
    ).all()
    org_ids = [oid for oid in org_rows if oid is not None]

    recipient_ids = {str(user.id)}
    if org_ids:
        member_rows = (
            await db.scalars(
                select(Membership.user_id).where(Membership.organization_id.in_(org_ids))
            )
        ).all()
        recipient_ids.update(str(uid) for uid in member_rows if uid is not None)

    message = {
        "type": "notification",
        "title": payload.get("title", "Notification"),
        "message": payload.get("message", ""),
        "severity": payload.get("severity", "info"),
    }

    delivered = 0
    for recipient_id in recipient_ids:
        if recipient_id in notification_manager.active_connections:
            await notification_manager.broadcast_to_user(recipient_id, message)
            delivered += 1

    return {"broadcast": True, "recipients": delivered}
