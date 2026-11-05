from typing import Annotated

from anomaly_core.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from anomaly_core.models.user import User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    count = await db.scalar(select(func.count()).select_from(User))
    if (count or 0) > 0:
        # Subsequent registrations require admin - full RBAC in Task 5.
        # For bootstrap safety, reject until admin flow exists.
        raise HTTPException(status_code=403, detail="Registration requires admin")
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    access = create_access_token(user.id, roles=[])
    refresh = await create_refresh_token(user.id, db)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    access = create_access_token(user.id, roles=[])
    refresh = await create_refresh_token(user.id, db)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    access, new_refresh = await rotate_refresh_token(body.refresh_token, db)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    await revoke_refresh_token(body.refresh_token, db)
    await db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
    )
