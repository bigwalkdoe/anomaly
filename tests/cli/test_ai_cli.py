from __future__ import annotations

import json

from anomaly_cli.main import app
from typer.testing import CliRunner


class Resp:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text or json.dumps(self._data)

    def json(self):
        return self._data


def test_ai_suggest_tools_help():
    runner = CliRunner()
    result = runner.invoke(app, ["ai", "suggest-tools", "--help"])
    assert result.exit_code == 0
    assert "suggest-tools" in result.output or "objective" in result.output


def test_ai_suggest_tools_structured(monkeypatch):
    runner = CliRunner()

    def fake_post(url, headers=None, json=None, timeout=None):
        return Resp(
            200,
            {
                "provider": "fake",
                "model": "m",
                "parse_success": True,
                "notes": "n",
                "raw": None,
                "suggestions": [
                    {
                        "tool": "nmap",
                        "reason": "scan",
                        "priority": "high",
                        "targets_hint": "host",
                        "params": {"p": "80"},
                    }
                ],
            },
        )

    monkeypatch.setattr("anomaly_cli.commands.ai.httpx.post", fake_post)
    result = runner.invoke(
        app,
        [
            "ai",
            "suggest-tools",
            "--objective",
            "scan host",
            "--api-url",
            "http://x",
            "--token",
            "t",
        ],
    )
    assert result.exit_code == 0
    assert "nmap" in result.output
    assert "scan" in result.output


def test_ai_suggest_tools_fallback(monkeypatch):
    runner = CliRunner()

    def fake_post(url, headers=None, json=None, timeout=None):
        return Resp(
            200,
            {
                "provider": "fake",
                "model": "m",
                "parse_success": False,
                "notes": None,
                "raw": "use nmap manually",
                "suggestions": [],
            },
        )

    monkeypatch.setattr("anomaly_cli.commands.ai.httpx.post", fake_post)
    result = runner.invoke(app, ["ai", "suggest-tools", "--objective", "scan host"])
    assert result.exit_code == 0
    assert "use nmap manually" in result.output
