from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="engagements", help="Engagement management")
console = Console()


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.command("create")
def create(
    name: str = typer.Option(..., "--name", help="Engagement name"),
    mode: str = typer.Option("own_infra", "--mode", help="own_infra | bug_bounty | client"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Create a new engagement."""
    r = httpx.post(
        f"{api_url}/api/engagements",
        headers=_headers(token or None),
        json={"name": name, "mode": mode, "status": "draft"},
    )
    if r.status_code not in (200, 201):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    table = Table(title="Engagement Created")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", str(data["id"]))
    table.add_row("Name", data["name"])
    table.add_row("Mode", data["mode"])
    table.add_row("Status", data["status"])
    console.print(table)
    console.print("\n[green]Use this ID for subsequent commands.[/green]")
    console.print(f"[dim]export ANOMALY_ENGAGEMENT_ID={data['id']}[/dim]")


@app.command("scope")
def scope(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    entry: list[str] = typer.Option(  # noqa: B008
        [], "--entry", help="Scope entry as 'in:example.com' or 'out:192.168.1.0/24'"
    ),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Set scope entries for an engagement."""
    entries = []
    for e in entry:
        if ":" not in e:
            console.print(f"[red]Invalid entry '{e}': use 'kind:value' (e.g. in:example.com)[/red]")
            raise typer.Exit(1)
        kind, value = e.split(":", 1)
        if kind not in ("in", "out"):
            console.print(f"[red]Invalid kind '{kind}': use 'in' or 'out'[/red]")
            raise typer.Exit(1)
        entries.append({"kind": kind, "target_value": value})

    r = httpx.put(
        f"{api_url}/api/engagements/{engagement_id}/scope",
        headers=_headers(token or None),
        json={"entries": entries},
    )
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Scope updated for engagement {engagement_id}[/green]")


@app.command("target")
def target(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    value: str = typer.Option(..., "--value", help="Target value (domain/IP/CIDR/URL)"),
    type: str = typer.Option("domain", "--type", help="domain | ip | cidr | url | service"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Add a target to an engagement."""
    r = httpx.post(
        f"{api_url}/api/engagements/{engagement_id}/targets",
        headers=_headers(token or None),
        json={"value": value, "type": type},
    )
    if r.status_code not in (200, 201):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    console.print(
        f"[green]Target added[/green] ID={data['id']} value={data['value']} type={data['type']}"
    )


@app.command("list")
def list_engagements(
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """List engagements."""
    r = httpx.get(f"{api_url}/api/engagements", headers=_headers(token or None))
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
        table.add_row(str(it["id"])[:8], it["name"], it["mode"], it["status"])
    console.print(table)
