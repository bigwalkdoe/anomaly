from __future__ import annotations

from uuid import UUID

from anomaly_core.auth import hash_password
from anomaly_core.models import APIKey
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: str = Field(default="*")


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    scopes: str
    is_active: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class APIKeyWithSecret(BaseModel):
    id: UUID
    name: str
    scopes: str
    key: str  # Only returned on creation


@router.post("", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    user: CurrentUser,
    db: DbSession,
):
    import secrets

    key = f"anomaly_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(key)
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        name=payload.name,
        scopes=payload.scopes,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return APIKeyWithSecret(
        id=api_key.id,
        name=api_key.name,
        scopes=api_key.scopes,
        key=key,
    )


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(user: CurrentUser, db: DbSession):
    result = await db.execute(select(APIKey).where(APIKey.user_id == user.id))
    keys = result.scalars().all()
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            scopes=k.scopes,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(key_id: UUID, user: CurrentUser, db: DbSession):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
    return None


@router.patch("/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(key_id: UUID, user: CurrentUser, db: DbSession):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    await db.commit()
    await db.refresh(api_key)
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
    )
