from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import docker


@dataclass
class RunSpec:
    tool: str
    image: str
    target_values: list[str]
    params: dict[str, Any]
    env: dict[str, str]
    timeout_s: int
    network: str
    resource_limits: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    artifacts: list[str] = field(default_factory=list)
    duration_s: float = 0.0


class RunnerBackend(Protocol):
    async def run(self, spec: RunSpec) -> RunResult: ...


class FakeRunner:
    def __init__(self, result: RunResult | None = None) -> None:
        self.result = result or RunResult(exit_code=0, stdout="", stderr="", artifacts=[], duration_s=0.0)
        self.specs: list[RunSpec] = []

    async def run(self, spec: RunSpec) -> RunResult:
        self.specs.append(spec)
        return self.result


class DockerRunner:
    async def run(self, spec: RunSpec) -> RunResult:
        client = docker.from_env()
        limits = dict(spec.resource_limits)
        kwargs: dict[str, Any] = {
            "image": spec.image,
            "network": spec.network,
            "environment": spec.env,
            "detach": True,
            "remove": False,
            "privileged": False,
            **limits,
        }
        container = client.containers.run(**kwargs)
        try:
            wait = container.wait(timeout=spec.timeout_s)
            status = wait.get("StatusCode", 1) if isinstance(wait, dict) else 1
            logs = container.logs(stdout=True, stderr=True)
            stdout = logs.decode("utf-8", errors="replace") if isinstance(logs, (bytes, bytearray)) else str(logs)
            return RunResult(exit_code=status, stdout=stdout, stderr="", artifacts=[], duration_s=0.0)
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
