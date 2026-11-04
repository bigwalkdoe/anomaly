from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import typer
from rich.table import Table
from rich.console import Console

app = typer.Typer(name="anomaly", help="Anomaly CLI")
console = Console()

CONFIG_DIR = Path.home() / ".config" / "anomaly"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {"api_url": os.environ.get("ANOMALY_API_URL", "http://localhost:8000"), "token": os.environ.get("ANOMALY_TOKEN")}


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


@app.command()
def auth_login(email: str = typer.Option(...), password: str = typer.Option(...)):
    """Login and save token"""
    cfg = load_config()
    r = httpx.post(f"{cfg['api_url']}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        console.print(f"[red]Login failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    data = r.json()
    cfg["token"] = data.get("access_token")
    save_config(cfg)
    console.print("[green]Logged in[/green]")


@app.command()
def engagements_list():
    """List engagements"""
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg.get('token')}"} if cfg.get("token") else {}
    r = httpx.get(f"{cfg['api_url']}/api/engagements", headers=headers)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    items = r.json()
    table = Table(title="Engagements")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Mode")
    table.add_column("Status")
    for it in items:
        table.add_row(it["id"][:8], it["name"], it["mode"], it["status"])
    console.print(table)


@app.command()
def runs_list(engagement_id: str):
    """List runs for an engagement"""
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg.get('token')}"} if cfg.get("token") else {}
    r = httpx.get(f"{cfg['api_url']}/api/engagements/{engagement_id}/runs", headers=headers)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    items = r.json()
    table = Table(title="Runs")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Scope Warning")
    for it in items:
        table.add_row(it["id"][:8], it["status"], str(it.get("scope_warning")))
    console.print(table)


@app.command()
def findings_list(engagement_id: str):
    """List findings for an engagement"""
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg.get('token')}"} if cfg.get("token") else {}
    r = httpx.get(f"{cfg['api_url']}/api/engagements/{engagement_id}/findings", headers=headers)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    items = r.json()
    table = Table(title="Findings")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Severity")
    table.add_column("Status")
    for it in items:
        table.add_row(it["id"][:8], it["title"], it["severity"], it["status"])
    console.print(table)


@app.command()
def version():
    console.print("anomaly-cli 0.1.0")


if __name__ == "__main__":
    app()
