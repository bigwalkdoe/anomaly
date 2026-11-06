from __future__ import annotations

from anomaly_core.audit import AuditService
from anomaly_core.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    generate_totp_uri,
    hash_backup_codes,
    verify_backup_code,
    verify_totp,
)
from anomaly_core.models import MFASecret
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/mfa", tags=["mfa"])


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MFAStatusResponse(BaseModel):
    is_enabled: bool


class MFABackupCodesResponse(BaseModel):
    backup_codes: list[str]


@router.post("/setup", response_model=MFASetupResponse, status_code=status.HTTP_201_CREATED)
async def setup_mfa(
    user: CurrentUser,
    db: DbSession,
):
    """Set up MFA for the current user. Returns secret, QR code URI, and backup codes."""
    # Check if MFA is already set up
    existing = await db.get(MFASecret, user.id)
    # MFASecret uses user_id as id, not a separate id. Let's query properly.
    from sqlalchemy import select

    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    existing = result.scalar_one_or_none()
    if existing and existing.is_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    backup_codes_hash = hash_backup_codes(backup_codes)
    provisioning_uri = generate_totp_uri(secret, user.email)

    if existing:
        existing.secret_key = secret
        existing.is_enabled = False  # Will be enabled after verification
        existing.backup_codes = backup_codes_hash
        await db.commit()
    else:
        mfa_secret = MFASecret(
            user_id=user.id,
            secret_key=secret,
            is_enabled=False,
            backup_codes=backup_codes_hash,
        )
        db.add(mfa_secret)
        await db.commit()

    await AuditService.log(
        actor_id=user.id,
        action="mfa.setup",
        resource_type="mfa",
        resource_id=user.id,
        metadata={"has_backup_codes": True},
        db=db,
    )

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        backup_codes=backup_codes,
    )


@router.post("/verify", response_model=MFAStatusResponse)
async def verify_mfa(
    payload: MFAVerifyRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Verify MFA setup with a TOTP code and enable MFA."""
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()
    if not mfa or not mfa.secret_key:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")

    if not verify_totp(mfa.secret_key, payload.code):
        await AuditService.log(
            actor_id=user.id,
            action="mfa.verify_failed",
            resource_type="mfa",
            resource_id=user.id,
            metadata={},
            db=db,
        )
        raise HTTPException(status_code=400, detail="Invalid verification code")

    mfa.is_enabled = True
    await db.commit()

    await AuditService.log(
        actor_id=user.id,
        action="mfa.enabled",
        resource_type="mfa",
        resource_id=user.id,
        metadata={},
        db=db,
    )

    return MFAStatusResponse(is_enabled=True)


@router.get("/status", response_model=MFAStatusResponse)
async def mfa_status(user: CurrentUser, db: DbSession):
    """Check if MFA is enabled for the current user."""
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()
    return MFAStatusResponse(is_enabled=bool(mfa and mfa.is_enabled))


@router.post("/disable", response_model=MFAStatusResponse)
async def disable_mfa(
    payload: MFAVerifyRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Disable MFA. Requires a valid TOTP code or backup code."""
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()
    if not mfa or not mfa.is_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    # Verify TOTP or backup code
    valid = verify_totp(mfa.secret_key, payload.code)
    if not valid and mfa.backup_codes:
        valid = verify_backup_code(mfa.backup_codes, payload.code)
        if valid:
            # Remove used backup code
            import hashlib
            import json

            code_hash = hashlib.sha256(payload.code.encode()).hexdigest()
            stored = json.loads(mfa.backup_codes or "[]")
            stored = [h for h in stored if h != code_hash]
            mfa.backup_codes = json.dumps(stored) if stored else None

    if not valid:
        await AuditService.log(
            actor_id=user.id,
            action="mfa.disable_failed",
            resource_type="mfa",
            resource_id=user.id,
            metadata={},
            db=db,
        )
        raise HTTPException(status_code=400, detail="Invalid verification code")

    mfa.is_enabled = False
    await db.commit()

    await AuditService.log(
        actor_id=user.id,
        action="mfa.disabled",
        resource_type="mfa",
        resource_id=user.id,
        metadata={},
        db=db,
    )

    return MFAStatusResponse(is_enabled=False)


@router.post("/backup-codes", response_model=MFABackupCodesResponse)
async def regenerate_backup_codes(
    payload: MFAVerifyRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Regenerate backup codes. Requires valid TOTP code."""
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()
    if not mfa or not mfa.is_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if not verify_totp(mfa.secret_key, payload.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    backup_codes = generate_backup_codes()
    mfa.backup_codes = hash_backup_codes(backup_codes)
    await db.commit()

    await AuditService.log(
        actor_id=user.id,
        action="mfa.backup_codes_regenerated",
        resource_type="mfa",
        resource_id=user.id,
        metadata={},
        db=db,
    )

    return MFABackupCodesResponse(backup_codes=backup_codes)


@router.post("/verify-login")
async def verify_mfa_login(
    payload: MFAVerifyRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Verify MFA during login. Accepts TOTP code or backup code."""
    result = await db.execute(select(MFASecret).where(MFASecret.user_id == user.id))
    mfa = result.scalar_one_or_none()
    if not mfa or not mfa.is_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    valid = verify_totp(mfa.secret_key, payload.code)
    if not valid and mfa.backup_codes:
        valid = verify_backup_code(mfa.backup_codes, payload.code)
        if valid:
            import hashlib
            import json

            code_hash = hashlib.sha256(payload.code.encode()).hexdigest()
            stored = json.loads(mfa.backup_codes or "[]")
            stored = [h for h in stored if h != code_hash]
            mfa.backup_codes = json.dumps(stored) if stored else None

    if not valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    await db.commit()

    await AuditService.log(
        actor_id=user.id,
        action="mfa.login_verified",
        resource_type="mfa",
        resource_id=user.id,
        metadata={},
        db=db,
    )

    return {"verified": True}
