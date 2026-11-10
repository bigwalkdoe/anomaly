from __future__ import annotations

from typing import Annotated, Any

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
from anomaly_core.models import LoginAttempt, MFASecret, Role, RoleName, User
from anomaly_core.rbac import ensure_default_rbac
from anomaly_core.tenancy import get_user_memberships
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from anomaly_api.deps import CurrentUser, DbSession, get_optional_user
from anomaly_api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MembershipResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _ensure_roles(db: DbSession) -> None:
    """Seed roles and their default permissions (idempotent, request-scoped)."""
    await ensure_default_rbac(db)


async def _user_response(user: User, db: DbSession) -> UserResponse:
    memberships = await get_user_memberships(db, user)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=[role.name.value for role in user.roles],
        memberships=[
            MembershipResponse(
                organization_id=m.organization_id,
                workspace_id=m.workspace_id,
                role=m.role,
            )
            for m in memberships
        ],
        organizations=list({m.organization_id for m in memberships}),
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
        current_user is None or not any(role.name == RoleName.admin for role in current_user.roles)
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


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    from datetime import UTC, datetime, timedelta

    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        # Record failed attempt and check lockout
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            email=payload.email,
            success=False,
        )
        db.add(attempt)
        await db.commit()

        # Check lockout: 5 failed attempts within 15 minutes
        lockout_window = datetime.now(UTC) - timedelta(minutes=15)
        result = await db.execute(
            select(LoginAttempt)
            .where(LoginAttempt.email == payload.email)
            .where(LoginAttempt.success == False)  # noqa: E712
            .where(LoginAttempt.created_at >= lockout_window)
        )
        recent_failures = result.scalars().all()
        if len(recent_failures) > 5:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Account temporarily locked due to too many failed login attempts. "
                    "Try again later."
                ),
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        # Record failed attempt for inactive user too
        attempt = LoginAttempt(
            user_id=user.id,
            email=payload.email,
            success=False,
        )
        db.add(attempt)
        await db.commit()
        raise HTTPException(status_code=401, detail="Inactive user")

    # Record successful attempt
    attempt = LoginAttempt(
        user_id=user.id,
        email=payload.email,
        success=True,
    )
    db.add(attempt)
    await db.commit()

    # Check if MFA is enabled for this user
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()

    if mfa and mfa.is_enabled:
        # MFA is enabled - require verification
        return LoginResponse(
            mfa_required=True,
            user_id=str(user.id),
        )

    # No MFA - issue tokens directly
    tokens = await _issue_tokens(db, user)
    await db.commit()
    return LoginResponse(
        mfa_required=False,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user_id=str(user.id),
    )


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
async def me(user: CurrentUser, db: DbSession) -> UserResponse:
    return await _user_response(user, db)


@router.get("/verify")
async def verify_token(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Basic token verification endpoint for client-side checks"""
    return {"valid": True}


@router.post("/logout", status_code=204)
async def logout_endpoint() -> None:
    # Client-side token revocation
    return None
