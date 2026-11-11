from __future__ import annotations

from anomaly_core.models import RoleName, Tag
from anomaly_core.rbac import has_role
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(user: CurrentUser, db: DbSession):
    tags = (await db.scalars(select(Tag))).all()
    return [{"id": str(t.id), "name": t.name, "color": t.color} for t in tags]


@router.post("")
async def create_tag(payload: dict, user: CurrentUser, db: DbSession):
    if not has_role(user, RoleName.admin):
        raise HTTPException(status_code=403, detail="Forbidden")
    tag = Tag(name=payload["name"], color=payload.get("color", "#666"))
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": str(tag.id), "name": tag.name}
