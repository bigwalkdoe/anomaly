from unittest.mock import MagicMock, patch

import pytest
from anomaly_core.runner import DockerRunner, FakeRunner, RunResult, RunSpec


@pytest.mark.asyncio
async def test_fake_runner_records_and_returns():
    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout="ok", stderr="", artifacts=[], duration_s=1.0)
    )
    spec = RunSpec(
        tool="stub",
        image="img",
        target_values=["example.com"],
        params={},
        env={},
        timeout_s=30,
        network="net",
        resource_limits={"mem": "128m"},
    )
    result = await runner.run(spec)
    assert result.exit_code == 0
    assert runner.specs == [spec]


@pytest.mark.asyncio
async def test_docker_runner_builds_args():
    runner = DockerRunner()
    spec = RunSpec(
        tool="stub",
        image="anomaly-runner:dev",
        target_values=["example.com"],
        params={"k": "v"},
        env={"A": "B"},
        timeout_s=60,
        network="anomaly-net",
        resource_limits={"mem_limit": "256m", "cpu_period": 100000, "cpu_quota": 50000},
    )
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"output"
    mock_client.containers.run.return_value = mock_container
    with patch("anomaly_core.runner.docker.from_env", return_value=mock_client):
        result = await runner.run(spec)
    assert result.exit_code == 0
    kwargs = mock_client.containers.run.call_args.kwargs
    assert kwargs["image"] == "anomaly-runner:dev"
    assert kwargs["network"] == "anomaly-net"
    assert kwargs.get("privileged") is not True
    assert kwargs.get("mem_limit") == "256m"


def test_runspec_accepts_optional_command():
    spec = RunSpec(
        tool="nmap",
        image="img",
        target_values=["x"],
        params={},
        env={},
        timeout_s=1,
        network="n",
        command=["nmap", "-sS", "x"],
    )
    assert spec.command == ["nmap", "-sS", "x"]
