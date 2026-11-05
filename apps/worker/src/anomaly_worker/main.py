from anomaly_core.config import get_settings
from arq.connections import RedisSettings

from anomaly_worker.tasks import execute_run


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    # Parse redis://host:port/db minimally.
    url = settings.redis_url.replace("redis://", "")
    host_port, _, db = url.partition("/")
    host, _, port = host_port.partition(":")
    return RedisSettings(host=host or "localhost", port=int(port or 6379), database=int(db or 0))


class WorkerSettings:
    functions = [execute_run]
    redis_settings = _redis_settings()
    max_jobs = 10
