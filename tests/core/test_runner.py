from __future__ import annotations

import pytest

from anomaly_core.runner import DockerRunner, FakeRunner, RunResult, RunSpec


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
