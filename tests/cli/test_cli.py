from __future__ import annotations

from typer.testing import CliRunner

from anomaly_cli.main import app


def test_version():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "anomaly-cli" in result.output
