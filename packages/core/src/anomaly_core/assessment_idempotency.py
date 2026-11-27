from __future__ import annotations

import hashlib

MAX_IDEMPOTENCY_KEY_LENGTH = 255


class InvalidIdempotencyKey(ValueError):
    """Raised when a client-supplied idempotency key is unusable."""


def normalize_idempotency_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = raw.strip()
    if not key or len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise InvalidIdempotencyKey("Idempotency-Key must be 1-255 non-blank characters")
    return key


def hash_idempotency_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
