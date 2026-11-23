from __future__ import annotations

import pytest
from anomaly_core.runner import DockerRunner, FakeRunner, RunResult, RunSpec


def test_runspec_accepts_optional_command():
    spec = RunSpec(
        tool="nmap",
        image="anomaly-runner:dev",
        target_values=["example.com"],
        command=["nmap", "-sV", "example.com"],
    )
    assert spec.command == ["nmap", "-sV", "example.com"]


def test_runspec_command_defaults_to_none():
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev", target_values=["example.com"])
    assert spec.command is None


@pytest.mark.asyncio
async def test_fake_runner_records_spec_and_returns_result():
    runner = FakeRunner(result=RunResult(exit_code=0, stdout="ok"))
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev", target_values=["example.com"])
    res = await runner.run(spec)
    assert res.exit_code == 0
    assert runner.specs[0].tool == "nmap"


def test_docker_runner_builds_correct_args():
    runner = DockerRunner(network="anomaly-net")
    spec = RunSpec(
        tool="nmap",
        image="anomaly-runner:dev",
        target_values=["example.com"],
        env={"FOO": "bar"},
        resource_limits={"mem_limit": "512m", "cpu_period": 100000, "cpu_quota": 50000},
    )
    args = runner._build_args(spec)
    assert args["network"] == "anomaly-net"
    assert args["privileged"] is False
    assert args["mem_limit"] == "512m"
    assert args["read_only"] is True
    assert args["cap_drop"] == ["ALL"]
    assert args["security_opt"] == ["no-new-privileges:true"]
    assert args["pids_limit"] == 256
    assert "/tmp" in args["tmpfs"]


def test_docker_runner_defaults_to_no_network():
    runner = DockerRunner()
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev")
    args = runner._build_args(spec)
    assert args["network"] == "none"


@pytest.mark.asyncio
async def test_docker_runner_without_client_returns_error_result():
    runner = DockerRunner(client=None)
    runner.client = None
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev")
    res = await runner.run(spec)
    assert res.exit_code == 125
    assert "unavailable" in res.stderr.lower()


class _FakeContainer:
    def __init__(self, *, status_code=0, stdout=b"ok", stderr=b"", wait_exc=None):
        self.status_code = status_code
        self._stdout = stdout
        self._stderr = stderr
        self.wait_exc = wait_exc
        self.killed = False
        self.removed = False

    def wait(self, timeout=None):
        if self.wait_exc:
            raise self.wait_exc
        return {"StatusCode": self.status_code}

    def logs(self, stdout=True, stderr=False):
        if stdout and not stderr:
            return self._stdout
        if stderr and not stdout:
            return self._stderr
        return self._stdout + self._stderr

    def kill(self):
        self.killed = True

    def remove(self, force=True):
        self.removed = True


class _FakeContainers:
    def __init__(self, container):
        self._container = container
        self.last_kwargs = None

    def run(self, **kwargs):
        self.last_kwargs = kwargs
        return self._container


class _FakeDockerClient:
    def __init__(self, container):
        self.containers = _FakeContainers(container)


@pytest.mark.asyncio
async def test_docker_runner_executes_and_cleans_up_container():
    container = _FakeContainer(status_code=0, stdout=b"hello", stderr=b"")
    runner = DockerRunner(client=_FakeDockerClient(container), network="none")
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev", command=["echo", "hi"], timeout_s=5)
    res = await runner.run(spec)
    assert res.exit_code == 0
    assert res.stdout == "hello"
    assert container.removed is True
    assert runner.client.containers.last_kwargs["read_only"] is True
    assert runner.client.containers.last_kwargs["network"] == "none"


@pytest.mark.asyncio
async def test_docker_runner_timeout_kills_and_returns_124():
    container = _FakeContainer(wait_exc=TimeoutError("timed out"), stdout=b"partial", stderr=b"")
    runner = DockerRunner(client=_FakeDockerClient(container))
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev", timeout_s=1)
    res = await runner.run(spec)
    assert res.exit_code == 124
    assert container.killed is True
    assert container.removed is True
    assert "timed out" in res.stderr.lower()


@pytest.mark.asyncio
async def test_docker_runner_caps_large_output():
    from anomaly_core.runner import MAX_RUNNER_OUTPUT_BYTES

    big = b"A" * (MAX_RUNNER_OUTPUT_BYTES + 100)
    container = _FakeContainer(status_code=0, stdout=big, stderr=b"")
    runner = DockerRunner(client=_FakeDockerClient(container))
    spec = RunSpec(tool="nmap", image="anomaly-runner:dev", command=["echo", "hi"], timeout_s=5)
    res = await runner.run(spec)
    assert res.exit_code == 0
    assert "[output truncated]" in res.stdout
    assert len(res.stdout.encode("utf-8")) <= MAX_RUNNER_OUTPUT_BYTES + 64
