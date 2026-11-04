from __future__ import annotations

from anomaly_core.models import Tag
from fastapi import APIRouter
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(user: CurrentUser, db: DbSession):
    tags = (await db.scalars(select(Tag))).all()
    return [{"id": str(t.id), "name": t.name, "color": t.color} for t in tags]


@router.post("")
async def create_tag(payload: dict, user: CurrentUser, db: DbSession):
    tag = Tag(name=payload["name"], color=payload.get("color", "#666"))
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": str(tag.id), "name": tag.name}
