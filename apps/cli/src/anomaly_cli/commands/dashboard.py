from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

DEFAULT_TIMEOUT = 30.0


def _call(method: str, url: str, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    fn = {
        "GET": httpx.get,
        "POST": httpx.post,
        "PUT": httpx.put,
        "PATCH": httpx.patch,
        "DELETE": httpx.delete,
    }[method.upper()]
    try:
        return fn(url, **kwargs)
    except httpx.RequestError as exc:
        console.print(f"[red]Request failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Unexpected error: {exc}[/red]")
        raise typer.Exit(1) from exc


@app.command()
def summary(
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Show vulnerability summary"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = _call("GET", f"{api_url}/api/vulnerabilities/summary", headers=headers)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    try:
        data = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid response: {exc}[/red]")
        raise typer.Exit(1) from exc
    table = Table(title="Vulnerability Summary")
    table.add_column("Severity")
    table.add_column("Count", justify="right")
    for sev in ["critical", "high", "medium", "low"]:
        table.add_row(sev.capitalize(), str(data.get(sev, 0)))
    table.add_row("Total", str(data.get("total", 0)), style="bold")
    console.print(table)
