from __future__ import annotations

from uuid import UUID

from anomaly_core.models import RoleName, Tag
from anomaly_core.rbac import has_role
from anomaly_core.tenancy import get_or_create_default_organization, get_user_memberships
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(user: CurrentUser, db: DbSession):
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    memberships = await get_user_memberships(db, user)
    org_ids = [m.organization_id for m in memberships if m.organization_id is not None]
    if not org_ids:
        return []
    tags = (
        await db.scalars(
            select(Tag).where(Tag.organization_id.in_(org_ids)).order_by(Tag.name.asc())
        )
    ).all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "color": t.color,
            "organization_id": str(t.organization_id) if t.organization_id else None,
        }
        for t in tags
    ]


@router.post("")
async def create_tag(payload: dict, user: CurrentUser, db: DbSession):
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    memberships = await get_user_memberships(db, user)
    org_ids = {m.organization_id for m in memberships if m.organization_id is not None}
    requested_org = payload.get("organization_id")
    if requested_org:
        try:
            org_id = UUID(str(requested_org))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid organization_id") from None
        if org_id not in org_ids:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        org = await get_or_create_default_organization(db, user)
        org_id = org.id

    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    existing = await db.scalar(
        select(Tag).where(Tag.organization_id == org_id, Tag.name == name)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(name=name, color=payload.get("color", "#666"), organization_id=org_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {
        "id": str(tag.id),
        "name": tag.name,
        "color": tag.color,
        "organization_id": str(tag.organization_id) if tag.organization_id else None,
    }
