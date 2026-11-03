from __future__ import annotations

from anomaly_core.db import SessionLocal

from .executor import execute_run


async def execute_run_task(ctx, run_id: str):
    async with SessionLocal() as db:
        return await execute_run(db, run_id)
