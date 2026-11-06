from __future__ import annotations

from arq.connections import RedisSettings

from .tasks import execute_run_task


class WorkerSettings:
    functions = [execute_run_task]
    redis_settings = RedisSettings()
    max_jobs = 10
