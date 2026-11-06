from __future__ import annotations

from typing import Any
from uuid import UUID

from anomaly_core.db import SessionLocal

from .executor import execute_run


async def execute_run_task(ctx: Any, run_id: str) -> Any:
    async with SessionLocal() as db:
        return await execute_run(db, UUID(run_id))
