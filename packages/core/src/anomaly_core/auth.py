from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.config import get_settings
from anomaly_core.models.user import RefreshToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


@dataclass
class TokenPayload:
    sub: str
    type: str
    roles: list[str] | None = None
    jti: str | None = None
    family: str | None = None
    exp: int | None = None
    iat: int | None = None


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID | str, roles: list[str] | None = None) -> str:
    settings = get_settings()
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles or [],
        "type": "access",
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_min),
        "iat": now,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


async def create_refresh_token(
    user_id: uuid.UUID | str,
    db: AsyncSession,
    family_id: uuid.UUID | None = None,
) -> str:
    settings = get_settings()
    now = _now()
    jti = str(uuid.uuid4())
    family = family_id or uuid.uuid4()
    exp = now + timedelta(days=settings.jwt_refresh_ttl_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": exp,
        "iat": now,
        "jti": jti,
        "family": str(family),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    db.add(
        RefreshToken(
            user_id=uuid.UUID(str(user_id)),
            jti_hash=_hash_jti(jti),
            family_id=family,
            revoked=False,
            expires_at=exp,
        )
    )
    await db.flush()
    return token


def decode_token(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    return TokenPayload(
        sub=str(data.get("sub")),
        type=str(data.get("type", "")),
        roles=data.get("roles"),
        jti=data.get("jti"),
        family=data.get("family"),
        exp=data.get("exp"),
        iat=data.get("iat"),
    )


async def rotate_refresh_token(token: str, db: AsyncSession) -> tuple[str, str]:
    payload = decode_token(token)
    if payload.type != "refresh" or not payload.jti or not payload.family:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    jti_hash = _hash_jti(payload.jti)
    family_id = uuid.UUID(payload.family)
    result = await db.scalar(select(RefreshToken).where(RefreshToken.jti_hash == jti_hash))
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if result.revoked:
        # Theft detection: revoke entire family.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked=True)
        )
        await db.flush()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")
    result.revoked = True
    user = await db.scalar(select(User).where(User.id == result.user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    roles = []  # roles resolved in deps/router as needed
    access = create_access_token(user.id, roles)
    refresh = await create_refresh_token(user.id, db, family_id=family_id)
    return access, refresh


async def revoke_refresh_token(token: str, db: AsyncSession) -> None:
    try:
        payload = decode_token(token)
    except HTTPException:
        return
    if payload.type != "refresh" or not payload.jti:
        return
    jti_hash = _hash_jti(payload.jti)
    row = await db.scalar(select(RefreshToken).where(RefreshToken.jti_hash == jti_hash))
    if row:
        row.revoked = True
        await db.flush()
