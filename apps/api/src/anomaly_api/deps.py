from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated

from anomaly_core.auth import decode_token
from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, RoleName, User
from anomaly_core.rbac import engagement_accessible, has_permission
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except HTTPException:
        return None
    if payload.type != "access":
        return None
    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: RoleName) -> Callable[..., Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if not any(role.name in roles for role in user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return dependency


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    """FastAPI dependency factory: resolve the current user, then check a permission.

    Admins hold the "*" permission and always pass. Nested inside
    ``require_engagement_access`` (via ``use_cache=False``) it re-uses the same
    resolved user.
    """

    async def dependency(user: CurrentUser) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return user

    return dependency


def require_engagement_access(
    engagement_id_param: str = "engagement_id",
    min_role: RoleName = RoleName.client_viewer,
) -> Callable[..., Awaitable[Engagement]]:
    async def dependency(
        request: Request,
        user: CurrentUser,
        db: DbSession,
    ) -> Engagement:
        engagement_id = request.path_params.get(engagement_id_param)
        if engagement_id is None:
            raise HTTPException(status_code=400, detail="Missing engagement_id")
        try:
            engagement_uuid = uuid.UUID(str(engagement_id))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid engagement_id") from None
        engagement = await db.get(Engagement, engagement_uuid)
        if engagement is None:
            raise HTTPException(status_code=404, detail="Engagement not found")
        if not await engagement_accessible(db, user, engagement, min_role=min_role):
            raise HTTPException(status_code=403, detail="Forbidden")
        return engagement

    return dependency
