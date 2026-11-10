from __future__ import annotations

import json

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="ai", help="AI-assisted suggestions")
console = Console()


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.command("suggest-tools")
def suggest_tools(
    objective: str = typer.Option(..., "--objective", help="Objective or question for suggestions"),
    context_json: str = typer.Option("", "--context-json", help="Optional JSON context object"),
    engagement_id: str = typer.Option("", "--engagement-id", help="Optional engagement ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    token: str = typer.Option("", "--token"),
):
    """Suggest tools/next steps for an objective using the AI layer."""
    context = None
    if context_json:
        try:
            context = json.loads(context_json)
        except Exception as exc:
            console.print("[red]Invalid --context-json: must be valid JSON[/red]")
            raise typer.Exit(1) from exc

    payload = {"objective": objective, "context": context}
    if engagement_id:
        payload["engagement_id"] = engagement_id

    r = httpx.post(
        f"{api_url}/api/ai/suggest-tools",
        headers=_headers(token or None),
        json=payload,
        timeout=60,
    )
    if r.status_code != 200:
        console.print(f"[red]Failed: {r.status_code} {r.text}[/red]")
        raise typer.Exit(1)
    data = r.json()

    parse_success = data.get("parse_success", False)
    suggestions = data.get("suggestions") or []
    notes = data.get("notes")
    raw = data.get("raw")

    if parse_success and suggestions:
        table = Table(title="AI Tool Suggestions")
        table.add_column("Tool")
        table.add_column("Priority")
        table.add_column("Reason")
        table.add_column("Targets")
        table.add_column("Params")
        for s in suggestions:
            params = s.get("params") or {}
            try:
                params_str = json.dumps(params, default=str)
            except Exception:
                params_str = str(params)
            table.add_row(
                str(s.get("tool", "")),
                str(s.get("priority", "")),
                str(s.get("reason", "")),
                str(s.get("targets_hint", "")),
                params_str,
            )
        console.print(table)
        if notes:
            console.print(f"[dim]Notes:[/dim] {notes}")
    else:
        console.print(
            "[yellow]Could not parse structured suggestions; showing raw output:[/yellow]"
        )
        if raw:
            console.print(raw)
        elif notes:
            console.print(notes)
        else:
            console.print("(no output)")
