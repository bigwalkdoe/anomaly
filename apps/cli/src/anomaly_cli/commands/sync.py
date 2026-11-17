from __future__ import annotations

import httpx
import typer
from rich.console import Console

app = typer.Typer(name="sync", help="Sync external data (e.g. spectre)")
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
    r = _call("GET", f"{spectre_url}/api/security/summary")
    if r.status_code != 200:
        console.print(f"[red]spectre-agent unavailable: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    try:
        data = r.json()
    except Exception as exc:
        console.print(f"[red]Invalid spectre-agent response: {exc}[/red]")
        raise typer.Exit(1) from exc

    findings = data.get("findings") or data.get("vulnerabilities") or []
    created = 0
    failed = 0
    for f in findings if isinstance(findings, list) else []:
        if not isinstance(f, dict):
            failed += 1
            continue
        payload = {
            "title": f.get("title", "spectre finding"),
            "severity": f.get("severity", "info"),
            "description": f.get("description", ""),
        }
        try:
            rr = httpx.post(
                f"{api_url}/api/engagements/{engagement_id}/findings",
                headers=_headers(token or None),
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
        except httpx.RequestError:
            failed += 1
            continue
        except Exception:
            failed += 1
            continue
        if rr.status_code in (200, 201):
            created += 1
        else:
            failed += 1

    msg = f"Synced {created} findings from spectre-agent"
    if failed:
        console.print(f"[yellow]{msg} ({failed} failed)[/yellow]")
    else:
        console.print(f"[green]{msg}[/green]")


@app.command("status")
def sync_status():
    """Show sync capability status."""
    console.print("Supported sources: spectre-agent (GET /api/security/summary)")
    console.print("Use: anomaly sync spectre --id <engagement-id>")
