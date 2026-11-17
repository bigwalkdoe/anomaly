from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="findings", help="Finding management")
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
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    title: str = typer.Option(..., "--title", help="Finding title"),
    severity: str = typer.Option(
        "medium", "--severity", help="info | low | medium | high | critical"
    ),
    description: str = typer.Option("", "--description", help="Finding description"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Create a finding."""
    r = _call(
        "POST",
        f"{api_url}/api/engagements/{engagement_id}/findings",
        headers=_headers(token or None),
        json={"title": title, "severity": severity, "description": description},
    )
    if r.status_code not in (200, 201):
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    console.print(
        f"[green]Finding created[/green] ID={data.get('id', '-')} "
        f"title={data.get('title', '-')} severity={data.get('severity', '-')}"
    )


@app.command("update")
def update(
    finding_id: str = typer.Option(..., "--id", help="Finding ID"),
    title: str = typer.Option("", "--title"),
    severity: str = typer.Option("", "--severity"),
    status: str = typer.Option("", "--status"),
    description: str = typer.Option("", "--description"),
    remediation: str = typer.Option("", "--remediation"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Update a finding."""
    payload = {}
    if title:
        payload["title"] = title
    if severity:
        payload["severity"] = severity
    if status:
        payload["status"] = status
    if description:
        payload["description"] = description
    if remediation:
        payload["remediation"] = remediation

    r = _call(
        "PATCH",
        f"{api_url}/api/findings/{finding_id}",
        headers=_headers(token or None),
        json=payload,
    )
    if r.status_code == 404:
        console.print("[red]Finding not found[/red]")
        raise typer.Exit(1)
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()
    console.print(
        f"[green]Finding updated[/green] ID={data.get('id', '-')} status={data.get('status', '-')}"
    )


@app.command("list")
def list_findings(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """List findings for an engagement."""
    r = _call(
        "GET",
        f"{api_url}/api/engagements/{engagement_id}/findings",
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
    table = Table(title="Findings")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Severity")
    table.add_column("Status")
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        table.add_row(
            str(it.get("id", "-"))[:8],
            str(it.get("title", "-")),
            str(it.get("severity", "-")),
            str(it.get("status", "-")),
        )
    console.print(table)
