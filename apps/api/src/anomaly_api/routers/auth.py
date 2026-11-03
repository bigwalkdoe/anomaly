from __future__ import annotations

from typing import Annotated

from anomaly_core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
    verify_password,
)
from anomaly_core.models import Role, RoleName, User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession, get_optional_user
from anomaly_api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_DEFAULT_ROLES = {
    RoleName.admin: "Full platform administrator",
    RoleName.pentester: "Runs tools and manages findings",
    RoleName.client_viewer: "Read-only access to an engagement",
}


async def _ensure_roles(db: DbSession) -> None:
    existing = set((await db.scalars(select(Role.name))).all())
    for name, description in _DEFAULT_ROLES.items():
        if name not in existing:
            db.add(Role(name=name, description=description))
    await db.flush()


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=[role.name.value for role in user.roles],
    )


async def _issue_tokens(db: DbSession, user: User) -> TokenResponse:
    access = create_access_token(user.id, [role.name.value for role in user.roles])
    refresh = create_refresh_token(user.id)
    await store_refresh_token(db, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: DbSession,
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> TokenResponse:
    await _ensure_roles(db)
    user_count = await db.scalar(select(func.count(User.id)))
    is_first_user = (user_count or 0) == 0

    if not is_first_user and (
        current_user is None
        or not any(role.name == RoleName.admin for role in current_user.roles)
    ):
        raise HTTPException(status_code=403, detail="Only admins may register users")

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    role_name = RoleName.admin if is_first_user else RoleName.pentester
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise HTTPException(status_code=500, detail="Role seed missing")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        roles=[role],
    )
    db.add(user)
    await db.flush()

    tokens = await _issue_tokens(db, user)
    await db.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    tokens = await _issue_tokens(db, user)
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    access, refresh_token = await rotate_refresh_token(db, payload.refresh_token)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DbSession) -> None:
    token_payload = decode_token(payload.refresh_token)
    if token_payload.type != "refresh":
        raise HTTPException(status_code=400, detail="Not a refresh token")
    await revoke_refresh_token(db, token_payload)
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return _user_response(user)
