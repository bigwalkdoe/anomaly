from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="reports", help="Report generation")
console = Console()


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.command("generate")
def generate(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    format: str = typer.Option("markdown", "--format", help="markdown | html | pdf"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Generate a report for an engagement."""
    r = httpx.get(
        f"{api_url}/api/reports/engagements/{engagement_id}/generate",
        headers=_headers(token or None),
        params={"format": format},
    )
    if r.status_code == 404:
        console.print("[red]Engagement not found[/red]")
        raise typer.Exit(1)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    console.print(
        f"[green]Report generated[/green] format={data['format']} "
        f"findings={data['finding_count']}"
    )
    console.print(data["content"])


@app.command("list")
def list_reports(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """List reports for an engagement (metadata via dashboard/stats is available)."""
    r = httpx.get(
        f"{api_url}/api/engagements/{engagement_id}",
        headers=_headers(token or None),
    )
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code}[/red]")
        raise typer.Exit(1)
    data = r.json()
    table = Table(title=f"Engagement {engagement_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Name", data["name"])
    table.add_row("Mode", data["mode"])
    table.add_row("Status", data["status"])
    table.add_row("Client", data.get("client_name") or "-")
    console.print(table)
