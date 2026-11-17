from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="reports", help="Report generation")
console = Console()

DEFAULT_TIMEOUT = 30.0


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


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


@app.command("generate")
def generate(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    format: str = typer.Option("markdown", "--format", help="markdown | html | pdf"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Generate a report for an engagement."""
    r = _call(
        "GET",
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
    try:
        data = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid response: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]Report generated[/green] format={data.get('format', format)} "
        f"findings={data.get('finding_count', '-')}"
    )
    if data.get("content") is not None:
        console.print(data.get("content"))


@app.command("list")
def list_reports(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Show engagement summary (report metadata endpoint is not yet available)."""
    r = _call(
        "GET",
        f"{api_url}/api/engagements/{engagement_id}",
        headers=_headers(token or None),
    )
    if r.status_code == 404:
        console.print("[red]Engagement not found[/red]")
        raise typer.Exit(1)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    try:
        data = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid response: {exc}[/red]")
        raise typer.Exit(1) from exc
    table = Table(title=f"Engagement {engagement_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Name", str(data.get("name", "-")))
    table.add_row("Mode", str(data.get("mode", "-")))
    table.add_row("Status", str(data.get("status", "-")))
    table.add_row("Client", str(data.get("client_name") or "-"))
    console.print(table)
