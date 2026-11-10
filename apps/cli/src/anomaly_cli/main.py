from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import typer
from rich.console import Console

from anomaly_cli.commands.ai import app as ai_app
from anomaly_cli.commands.config import app as config_app
from anomaly_cli.commands.dashboard import app as dashboard_app
from anomaly_cli.commands.engagements import app as engagements_app
from anomaly_cli.commands.findings import app as findings_app
from anomaly_cli.commands.reports import app as reports_app
from anomaly_cli.commands.runs import app as runs_app
from anomaly_cli.commands.sync import app as sync_app

app = typer.Typer(name="anomaly", help="Anomaly CLI")
console = Console()

CONFIG_DIR = Path.home() / ".config" / "anomaly"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {
        "api_url": os.environ.get("ANOMALY_API_URL", "http://localhost:8000"),
        "token": os.environ.get("ANOMALY_TOKEN"),
    }


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


@app.command("auth-login")
def auth_login(email: str = typer.Option(...), password: str = typer.Option(...)):
    """Login and save token."""
    cfg = load_config()
    r = httpx.post(
        f"{cfg['api_url']}/api/auth/login",
        json={"email": email, "password": password},
    )
    if r.status_code != 200:
        console.print(f"[red]Login failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    data = r.json()
    cfg["token"] = data.get("access_token")
    save_config(cfg)
    console.print("[green]Logged in[/green]")


app.add_typer(ai_app, name="ai")
app.add_typer(config_app, name="config")
app.add_typer(dashboard_app, name="dashboard")
app.add_typer(engagements_app, name="engagements")
app.add_typer(findings_app, name="findings")
app.add_typer(reports_app, name="reports")
app.add_typer(runs_app, name="runs")
app.add_typer(sync_app, name="sync")


@app.command()
def version():
    console.print("anomaly-cli 0.1.0")


if __name__ == "__main__":
    app()
