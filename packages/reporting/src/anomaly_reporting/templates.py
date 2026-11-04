from __future__ import annotations


def markdown_template(engagement_name: str, findings: list[dict]) -> str:
    lines = [f"# Report: {engagement_name}", "", "## Findings", ""]
    for f in findings:
        lines.append(f"### {f.get('title')} ({f.get('severity')})")
        lines.append(f.get('description', ''))
        lines.append("")
    return "\n".join(lines)
