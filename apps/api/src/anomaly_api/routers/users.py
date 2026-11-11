from __future__ import annotations

from anomaly_core.models import Membership, RoleName, User
from anomaly_core.rbac import has_role
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(user: CurrentUser, db: DbSession):
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    org_rows = (
        await db.scalars(
            select(Membership.organization_id).where(Membership.user_id == user.id)
        )
    ).all()
    org_ids = [oid for oid in org_rows if oid is not None]
    if org_ids:
        stmt = (
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.organization_id.in_(org_ids))
            .distinct()
        )
    else:
        stmt = select(User).where(User.id == user.id)
    users = (await db.scalars(stmt)).all()
    return [
        {"id": str(u.id), "email": u.email, "name": u.name, "is_active": u.is_active} for u in users
    ]


@router.get("/me")
async def get_me(user: CurrentUser):
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "roles": [r.name.value for r in user.roles],
    }
