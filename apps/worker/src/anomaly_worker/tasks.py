from __future__ import annotations

import uuid
from typing import Any

from anomaly_core.db import SessionLocal

from anomaly_worker.executor import execute_run_inline


async def execute_run(ctx: Any, run_id: str) -> None:
    async with SessionLocal() as db:
        await execute_run_inline(db, uuid.UUID(run_id))
