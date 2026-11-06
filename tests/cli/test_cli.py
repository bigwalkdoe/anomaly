from __future__ import annotations

from anomaly_cli.main import app
from typer.testing import CliRunner


def test_version():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "anomaly-cli" in result.output
