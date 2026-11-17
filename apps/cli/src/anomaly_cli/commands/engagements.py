from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="engagements", help="Engagement management")
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


@app.command("create")
def create(
    name: str = typer.Option(..., "--name", help="Engagement name"),
    mode: str = typer.Option("own_infra", "--mode", help="own_infra | bug_bounty | client"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Create a new engagement."""
    r = _call(
        "POST",
        f"{api_url}/api/engagements",
        headers=_headers(token or None),
        json={"name": name, "mode": mode},
    )
    if r.status_code not in (200, 201):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    table = Table(title="Engagement Created")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", str(data.get("id", "-")))
    table.add_row("Name", str(data.get("name", "-")))
    table.add_row("Mode", str(data.get("mode", "-")))
    table.add_row("Status", str(data.get("status", "-")))
    console.print(table)
    if data.get("id"):
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

    r = _call(
        "PUT",
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
    r = _call(
        "POST",
        f"{api_url}/api/engagements/{engagement_id}/targets",
        headers=_headers(token or None),
        json={"value": value, "type": type},
    )
    if r.status_code not in (200, 201):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    console.print(
        f"[green]Target added[/green] ID={data.get('id', '-')} "
        f"value={data.get('value', '-')} type={data.get('type', '-')}"
    )


@app.command("list")
def list_engagements(
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """List engagements."""
    r = _call("GET", f"{api_url}/api/engagements", headers=_headers(token or None))
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    try:
        items = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid response: {exc}[/red]")
        raise typer.Exit(1) from exc
    table = Table(title="Engagements")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Mode")
    table.add_column("Status")
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        table.add_row(
            str(it.get("id", "-"))[:8],
            str(it.get("name", "-")),
            str(it.get("mode", "-")),
            str(it.get("status", "-")),
        )
    console.print(table)
