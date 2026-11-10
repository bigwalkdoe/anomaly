from __future__ import annotations

import httpx
import typer
from rich.console import Console

app = typer.Typer(name="sync", help="Sync external data (e.g. spectre)")
console = Console()


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.command("spectre")
def sync_spectre(
    engagement_id: str = typer.Option(..., "--id", help="Engagement ID"),
    spectre_url: str = typer.Option(
        "http://localhost:8001", "--spectre-url", help="spectre-agent base URL"
    ),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Pull spectre-agent security summary into the engagement as findings."""
    r = httpx.get(f"{spectre_url}/api/security/summary", timeout=30)
    if r.status_code != 200:
        console.print(f"[red]spectre-agent unavailable: {r.status_code}[/red]")
        raise typer.Exit(1)
    data = r.json()

    findings = data.get("findings") or data.get("vulnerabilities") or []
    created = 0
    for f in findings:
        payload = {
            "title": f.get("title", "spectre finding"),
            "severity": f.get("severity", "info"),
            "description": f.get("description", ""),
        }
        rr = httpx.post(
            f"{api_url}/api/engagements/{engagement_id}/findings",
            headers=_headers(token or None),
            json=payload,
        )
        if rr.status_code in (200, 201):
            created += 1

    console.print(f"[green]Synced {created} findings from spectre-agent[/green]")


@app.command("status")
def sync_status():
    """Show sync capability status."""
    console.print("Supported sources: spectre-agent (GET /api/security/summary)")
    console.print("Use: anomaly sync spectre --id <engagement-id>")
