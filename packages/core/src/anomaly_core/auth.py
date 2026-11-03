from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.config import get_settings
from anomaly_core.models import RefreshToken

ALGORITHM = "HS256"
_BCRYPT_MAX_BYTES = 72


def _password_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_password_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    type: str
    jti: str
    exp: int
    iat: int
    roles: list[str] | None = None
    family: str | None = None


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID | str, roles: list[str] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "roles": roles or [],
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_min),
        "jti": uuid.uuid4().hex,
    }
    return _encode(payload)


def create_refresh_token(user_id: uuid.UUID | str, family_id: str | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_ttl_days),
        "jti": uuid.uuid4().hex,
        "family": family_id or uuid.uuid4().hex,
    }
    return _encode(payload)


def decode_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenPayload(
        sub=str(raw["sub"]),
        type=str(raw["type"]),
        jti=str(raw["jti"]),
        exp=int(raw["exp"]),
        iat=int(raw["iat"]),
        roles=list(raw.get("roles") or []),
        family=raw.get("family"),
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def store_refresh_token(db: AsyncSession, token: str) -> RefreshToken:
    payload = decode_token(token)
    record = RefreshToken(
        jti=payload.jti,
        user_id=uuid.UUID(payload.sub),
        family_id=payload.family or uuid.uuid4().hex,
        token_hash=_hash_token(token),
        expires_at=datetime.fromtimestamp(payload.exp, tz=UTC),
    )
    db.add(record)
    await db.flush()
    return record


async def revoke_refresh_token(db: AsyncSession, payload: TokenPayload) -> None:
    record = await db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.jti))
    if record is not None:
        record.revoked = True
        await db.flush()


async def revoke_family(db: AsyncSession, family_id: str) -> None:
    records = (
        await db.scalars(select(RefreshToken).where(RefreshToken.family_id == family_id))
    ).all()
    for record in records:
        record.revoked = True
    await db.flush()


async def rotate_refresh_token(
    db: AsyncSession, token: str
) -> tuple[str, str]:
    """Validate a refresh token, revoke it, and issue a new pair.

    Reuse of an already-revoked token revokes the whole family (theft
    detection) and raises 401.
    """
    payload = decode_token(token)
    if payload.type != "refresh" or payload.family is None:
        raise HTTPException(status_code=401, detail="Invalid token type")

    record = await db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.jti))
    if record is None:
        raise HTTPException(status_code=401, detail="Unknown refresh token")
    if record.revoked:
        await revoke_family(db, payload.family)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    record.revoked = True
    await db.flush()

    access = create_access_token(payload.sub)
    refresh = create_refresh_token(payload.sub, family_id=payload.family)
    await store_refresh_token(db, refresh)
    await db.flush()
    return access, refresh
