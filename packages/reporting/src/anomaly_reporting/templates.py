from __future__ import annotations

from typing import Any


def markdown_template(engagement_name: str, findings: list[dict], context: dict[str, Any] | None = None) -> str:
    ctx = context or {}
    lines = [f"# Report: {engagement_name}", ""]
    if ctx:
        lines.append("## Traceability")
        for key in ("organization_id", "engagement_id", "job_id", "run_id", "execution_id"):
            if key in ctx and ctx[key] is not None:
                lines.append(f"- {key}: {ctx[key]}")
        evidence_ids = ctx.get("evidence_ids") or []
        if evidence_ids:
            lines.append(f"- evidence_ids: {', '.join(str(x) for x in evidence_ids)}")
        evidence_shas = ctx.get("evidence_sha256") or ctx.get("evidence_checksums") or []
        if evidence_shas:
            lines.append(f"- evidence_sha256: {', '.join(str(x) for x in evidence_shas)}")
        lines.append("")
    lines.extend(["## Findings", ""])
    for f in findings:
        lines.append(f"### {f.get('title')} ({f.get('severity')})")
        desc = f.get("description", "")
        if desc:
            lines.append(desc)
        for key in ("run_id", "job_id", "execution_id", "evidence_sha256", "evidence_id"):
            if f.get(key):
                lines.append(f"- {key}: {f.get(key)}")
        lines.append("")
    return "\n".join(lines)
