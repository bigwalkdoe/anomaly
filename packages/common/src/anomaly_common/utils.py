from __future__ import annotations

import uuid
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_id() -> str:
    return str(uuid.uuid4())
