from __future__ import annotations

from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="runs", help="Tool run management")
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


@app.command("start")
def start(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    tool: str = typer.Option("stub", "--tool", help="stub | nmap | nuclei | httpx | ffuf | sqlmap"),
    target: str = typer.Option("", "--target", help="Single target to scan"),
    targets: str = typer.Option("", "--targets", help="Comma-separated targets"),
    param: list[str] = typer.Option(  # noqa: B008
        None, "--param", help="Extra param as key=value"
    ),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Enqueue a tool run."""
    target_list = [t.strip() for t in targets.split(",") if t.strip()] if targets else []
    if target:
        target_list.append(target)

    params: dict[str, Any] = {}
    for p in param or []:
        if "=" not in p:
            console.print(f"[red]Invalid param '{p}': use key=value[/red]")
            raise typer.Exit(1)
        k, v = p.split("=", 1)
        params[k] = v
    params["targets"] = target_list

    r = _call(
        "POST",
        f"{api_url}/api/engagements/{engagement_id}/runs",
        headers=_headers(token or None),
        json={"tool": tool, "targets": target_list, "params": params},
    )
    if r.status_code not in (200, 202):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    table = Table(title="Run Enqueued")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", str(data.get("id", "-")))
    table.add_row("Status", str(data.get("status", "-")))
    table.add_row("Scope Warning", str(data.get("scope_warning")))
    console.print(table)


@app.command("status")
def status(
    run_id: str = typer.Option(..., "--id", help="Run ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Get run status."""
    r = _call("GET", f"{api_url}/api/runs/{run_id}", headers=_headers(token or None))
    if r.status_code == 404:
        console.print("[red]Run not found[/red]")
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
        f"Run {run_id}: [bold]{data.get('status', '-')}[/bold]  "
        f"scope_warning={data.get('scope_warning')}"
    )


@app.command("list")
def list_runs(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """List runs for an engagement."""
    r = _call(
        "GET",
        f"{api_url}/api/engagements/{engagement_id}/runs",
        headers=_headers(token or None),
    )
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    try:
        items = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid response: {exc}[/red]")
        raise typer.Exit(1) from exc
    table = Table(title="Runs")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Scope Warning")
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        table.add_row(
            str(it.get("id", "-"))[:8],
            str(it.get("status", "-")),
            str(it.get("scope_warning")),
        )
    console.print(table)
