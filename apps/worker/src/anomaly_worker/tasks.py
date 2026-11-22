from __future__ import annotations

from typing import Any
from uuid import UUID

from anomaly_core.db import SessionLocal
from anomaly_core.scheduler import dispatch_due_schedules

from .executor import execute_run


async def execute_run_task(ctx: Any, run_id: str) -> Any:
    async with SessionLocal() as db:
        return await execute_run(db, UUID(run_id))


async def dispatch_schedules_task(ctx: Any) -> Any:
    async with SessionLocal() as db:
        return await dispatch_due_schedules(db)
