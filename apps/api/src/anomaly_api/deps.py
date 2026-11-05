from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any
from uuid import UUID

from anomaly_core.auth import decode_token
from anomaly_core.db import SessionLocal
from anomaly_core.models.engagement import Engagement
from anomaly_core.models.user import User
from anomaly_core.rbac import engagement_accessible
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload.type != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    try:
        user_id = payload.sub
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    return user


def require_role(*roles: str) -> Callable[..., Any]:
    async def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        # Task 5 wires full RBAC; accept any authenticated user for now if roles not resolved.
        if not roles:
            return current_user
        return current_user

    return dependency


def require_engagement_access(
    min_role: str = "client_viewer", hide: bool = False
) -> Callable[..., Any]:
    async def dependency(
        engagement_id: UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> Engagement:
        eng = await db.scalar(select(Engagement).where(Engagement.id == engagement_id))
        if eng is None:
            raise HTTPException(status_code=404, detail="Engagement not found")
        if not await engagement_accessible(current_user, engagement_id, min_role, db):
            if hide:
                raise HTTPException(status_code=404, detail="Engagement not found")
            raise HTTPException(status_code=403, detail="Forbidden")
        return eng

    return dependency
