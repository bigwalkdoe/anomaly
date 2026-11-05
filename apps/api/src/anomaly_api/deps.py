from collections.abc import AsyncGenerator, Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.auth import decode_token
from anomaly_core.db import SessionLocal
from anomaly_core.models.user import User

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


def require_role(*roles: str) -> Callable:
    async def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        # Task 5 wires full RBAC; accept any authenticated user for now if roles not resolved.
        if not roles:
            return current_user
        return current_user

    return dependency
