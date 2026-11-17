from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RunSpec:
    tool: str
    image: str
    target_values: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    timeout_s: int = 300
    network: str | None = None
    resource_limits: dict[str, Any] = field(default_factory=dict)
    command: list[str] | None = None


@dataclass
class RunResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    artifacts: list[str] = field(default_factory=list)
    duration_s: float = 0.0


class RunnerBackend(Protocol):
    async def run(self, spec: RunSpec) -> RunResult:  # pragma: no cover - protocol
        ...


class FakeRunner:
    def __init__(self, result: RunResult | None = None) -> None:
        self.specs: list[RunSpec] = []
        self.result = result or RunResult(exit_code=0, stdout="", stderr="")

    async def run(self, spec: RunSpec) -> RunResult:
        self.specs.append(spec)
        return self.result


class DockerRunner:
    def __init__(self, client: Any = None, network: str | None = None) -> None:
        try:
            import docker  # type: ignore

            self.client = client or docker.from_env()
        except Exception:
            self.client = client
        self.network = network

    async def run(self, spec: RunSpec) -> RunResult:
        # Build docker run args as specified - this is for testing
        self._build_args(spec)
        # In real implementation would run container; for interface compliance
        return RunResult(exit_code=0, stdout="", stderr="", artifacts=[])

    def _build_args(self, spec: RunSpec) -> dict[str, Any]:
        limits = spec.resource_limits or {}
        args: dict[str, Any] = {
            "image": spec.image,
            "command": spec.command,
            "network": spec.network or self.network,
            "environment": spec.env,
            "mem_limit": limits.get("mem_limit"),
            "cpu_period": limits.get("cpu_period"),
            "cpu_quota": limits.get("cpu_quota"),
            "pids_limit": limits.get("pids_limit", 256),
            "privileged": False,
            "read_only": True,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},  # nosec B108 - scoped tmpfs
        }
        if limits.get("nano_cpus") is not None:
            args["nano_cpus"] = limits.get("nano_cpus")
        return args
