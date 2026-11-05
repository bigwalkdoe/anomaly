from __future__ import annotations

import json
import secrets
import hashlib
from typing import Any

import pyotp


def generate_totp_secret() -> str:
    """Generate a new TOTP secret key (base32 encoded)."""
    return pyotp.random_base32()


def generate_totp_uri(secret: str, email: str, issuer: str = "Anomaly") -> str:
    """Generate a TOTP provisioning URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret key."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for MFA recovery."""
    return [secrets.token_hex(4) for _ in range(count)]


def hash_backup_codes(codes: list[str]) -> str:
    """Hash backup codes for storage."""
    import hashlib

    return json.dumps(
        [hashlib.sha256(code.encode()).hexdigest() for code in codes]
    )


def verify_backup_code(stored_hashes_json: str, code: str) -> bool:
    """Verify a backup code against stored hashes."""
    import hashlib

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    stored_hashes = json.loads(stored_hashes_json or "[]")
    return code_hash in stored_hashes
