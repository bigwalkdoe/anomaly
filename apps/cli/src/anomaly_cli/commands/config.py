from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="config", help="CLI configuration management")
console = Console()

CONFIG_DIR = Path.home() / ".config" / "anomaly"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {"api_url": os.environ.get("ANOMALY_API_URL", "http://localhost:8000"), "token": None}


@app.command("show")
def show():
    """Show current CLI configuration."""
    cfg = _load()
    table = Table(title="Anomaly CLI Config")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("api_url", cfg.get("api_url", "-"))
    token = cfg.get("token")
    table.add_row("token", "set" if token else "unset")
    console.print(table)


@app.command("set")
def set_config(
    api_url: str = typer.Option("", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Set CLI configuration values."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = _load()
    if api_url:
        cfg["api_url"] = api_url
    if token:
        cfg["token"] = token
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    console.print("[green]Configuration saved[/green]")


@app.command("unset")
def unset_config(token: bool = typer.Option(False, "--token", help="Clear the stored token")):
    """Clear configuration values."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = _load()
    if token:
        cfg["token"] = None
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    console.print("[green]Configuration cleared[/green]")
