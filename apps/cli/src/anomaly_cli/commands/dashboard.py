from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def summary(
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Show vulnerability summary"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = httpx.get(f"{api_url}/api/vulnerabilities/summary", headers=headers)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    data = r.json()
    table = Table(title="Vulnerability Summary")
    table.add_column("Severity")
    table.add_column("Count", justify="right")
    for sev in ["critical", "high", "medium", "low"]:
        table.add_row(sev.capitalize(), str(data.get(sev, 0)))
    table.add_row("Total", str(data.get("total", 0)), style="bold")
    console.print(table)
