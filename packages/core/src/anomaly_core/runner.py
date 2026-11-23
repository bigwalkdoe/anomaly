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
        import asyncio
        import time

        args = self._build_args(spec)
        if self.client is None:
            return RunResult(
                exit_code=125,
                stdout="",
                stderr="Docker client unavailable",
                artifacts=[],
                duration_s=0.0,
            )

        def _run_sync() -> RunResult:
            import contextlib

            started = time.monotonic()
            container = None
            try:
                container = self.client.containers.run(detach=True, **args)
                try:
                    wait_result = container.wait(timeout=max(1, int(spec.timeout_s)))
                except Exception:
                    with contextlib.suppress(Exception):
                        container.kill()
                    with contextlib.suppress(Exception):
                        container.wait(timeout=5)
                    duration = time.monotonic() - started
                    stdout = b""
                    stderr = b""
                    with contextlib.suppress(Exception):
                        stdout = container.logs(stdout=True, stderr=False) or b""
                        stderr = container.logs(stdout=False, stderr=True) or b""
                    timeout_msg = "\nExecution timed out"
                    return RunResult(
                        exit_code=124,
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=(stderr.decode("utf-8", errors="replace") + timeout_msg).strip(),
                        artifacts=[],
                        duration_s=duration,
                    )

                status_code = 1
                if isinstance(wait_result, dict):
                    status_code = int(wait_result.get("StatusCode", 1))
                else:
                    try:
                        status_code = int(wait_result)
                    except Exception:
                        status_code = 1
                stdout, stderr = b"", b""
                with contextlib.suppress(Exception):
                    stdout = container.logs(stdout=True, stderr=False) or b""
                    stderr = container.logs(stdout=False, stderr=True) or b""
                duration = time.monotonic() - started
                return RunResult(
                    exit_code=status_code,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    artifacts=[],
                    duration_s=duration,
                )
            except Exception as exc:
                duration = time.monotonic() - started
                return RunResult(
                    exit_code=125,
                    stdout="",
                    stderr=str(exc),
                    artifacts=[],
                    duration_s=duration,
                )
            finally:
                if container is not None:
                    with contextlib.suppress(Exception):
                        container.remove(force=True)

        return await asyncio.to_thread(_run_sync)

    def _build_args(self, spec: RunSpec) -> dict[str, Any]:
        limits = spec.resource_limits or {}
        network = spec.network if spec.network is not None else self.network
        if network is None:
            network = "none"
        args: dict[str, Any] = {
            "image": spec.image,
            "command": spec.command,
            "network": network,
            "environment": spec.env or None,
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
