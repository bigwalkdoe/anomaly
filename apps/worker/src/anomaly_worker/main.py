from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from .tasks import dispatch_schedules_task, execute_run_task


class WorkerSettings:
    functions = [execute_run_task]
    cron_jobs = [cron(dispatch_schedules_task, minute=None, second=0)]
    redis_settings = RedisSettings()
    max_jobs = 10
