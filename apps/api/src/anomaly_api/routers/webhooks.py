from __future__ import annotations

from anomaly_core.models import RoleName
from anomaly_core.rbac import has_role
from fastapi import APIRouter, HTTPException

from anomaly_api.deps import CurrentUser

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _require_admin(user: CurrentUser) -> None:
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
async def list_webhooks(user: CurrentUser):
    _require_admin(user)
    return []


@router.post("", status_code=501)
async def create_webhook(payload: dict, user: CurrentUser):
    _require_admin(user)
    raise HTTPException(status_code=501, detail="Webhooks are not implemented")
