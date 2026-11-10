from __future__ import annotations

import json

from anomaly_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


class Resp:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = text or json.dumps(self._data)

    def json(self):
        return self._data


def test_top_level_help_lists_new_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in [
        "config",
        "engagements",
        "findings",
        "reports",
        "runs",
        "sync",
        "ai",
        "dashboard",
    ]:
        assert name in result.output


def test_config_show_set_unset(monkeypatch, tmp_path):
    import anomaly_cli.commands.config as cfg_cmd

    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr(cfg_cmd, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg_cmd, "CONFIG_FILE", cfg_file)

    res = runner.invoke(app, ["config", "set", "--api-url", "http://api.test", "--token", "tok"])
    assert res.exit_code == 0
    assert "Configuration saved" in res.output
    saved = json.loads(cfg_file.read_text())
    assert saved["api_url"] == "http://api.test"
    assert saved["token"] == "tok"

    res = runner.invoke(app, ["config", "show"])
    assert res.exit_code == 0
    assert "http://api.test" in res.output
    assert "set" in res.output

    res = runner.invoke(app, ["config", "unset", "--token"])
    assert res.exit_code == 0
    saved = json.loads(cfg_file.read_text())
    assert saved["token"] is None


def test_engagements_list(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return Resp(
            200,
            [
                {
                    "id": "12345678-abcd-efgh",
                    "name": "Eng1",
                    "mode": "client",
                    "status": "active",
                }
            ],
        )

    monkeypatch.setattr("anomaly_cli.commands.engagements.httpx.get", fake_get)
    res = runner.invoke(app, ["engagements", "list", "--api-url", "http://x"])
    assert res.exit_code == 0
    assert "Eng1" in res.output
    assert "client" in res.output


def test_findings_list(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return Resp(
            200,
            [
                {
                    "id": "f2345678-abcd",
                    "title": "SQLi",
                    "severity": "high",
                    "status": "open",
                }
            ],
        )

    monkeypatch.setattr("anomaly_cli.commands.findings.httpx.get", fake_get)
    res = runner.invoke(app, ["findings", "list", "--id", "eng-1", "--api-url", "http://x"])
    assert res.exit_code == 0
    assert "SQLi" in res.output
    assert "high" in res.output


def test_runs_start_and_status(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(("post", url, json))
        return Resp(202, {"id": "run-12345678", "status": "queued", "scope_warning": False})

    def fake_get(url, headers=None, timeout=None):
        calls.append(("get", url, None))
        return Resp(200, {"id": "run-12345678", "status": "running", "scope_warning": False})

    monkeypatch.setattr("anomaly_cli.commands.runs.httpx.post", fake_post)
    monkeypatch.setattr("anomaly_cli.commands.runs.httpx.get", fake_get)

    res = runner.invoke(
        app,
        [
            "runs",
            "start",
            "--id",
            "eng-1",
            "--tool",
            "nmap",
            "--target",
            "10.0.0.1",
            "--param",
            "ports=80",
            "--api-url",
            "http://x",
        ],
    )
    assert res.exit_code == 0
    assert "Run Enqueued" in res.output
    assert calls[0][2]["tool"] == "nmap"
    assert "10.0.0.1" in calls[0][2]["targets"]
    assert calls[0][2]["params"]["ports"] == "80"

    res = runner.invoke(app, ["runs", "status", "--id", "run-12345678", "--api-url", "http://x"])
    assert res.exit_code == 0
    assert "running" in res.output


def test_reports_generate(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        return Resp(
            200,
            {"format": "markdown", "finding_count": 2, "content": "# Report\nBody"},
        )

    monkeypatch.setattr("anomaly_cli.commands.reports.httpx.get", fake_get)
    res = runner.invoke(
        app,
        [
            "reports",
            "generate",
            "--id",
            "eng-1",
            "--format",
            "markdown",
            "--api-url",
            "http://x",
        ],
    )
    assert res.exit_code == 0
    assert "Report generated" in res.output
    assert "# Report" in res.output


def test_sync_status_and_spectre(monkeypatch):
    res = runner.invoke(app, ["sync", "status"])
    assert res.exit_code == 0
    assert "spectre-agent" in res.output

    posts = []

    def fake_get(url, headers=None, timeout=None):
        return Resp(200, {"findings": [{"title": "X", "severity": "low", "description": "d"}]})

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append((url, json))
        return Resp(201, {"id": "f1"})

    monkeypatch.setattr("anomaly_cli.commands.sync.httpx.get", fake_get)
    monkeypatch.setattr("anomaly_cli.commands.sync.httpx.post", fake_post)
    res = runner.invoke(
        app,
        ["sync", "spectre", "--id", "eng-1", "--spectre-url", "http://s", "--api-url", "http://x"],
    )
    assert res.exit_code == 0
    assert "Synced 1 findings" in res.output
    assert posts and posts[0][1]["title"] == "X"
