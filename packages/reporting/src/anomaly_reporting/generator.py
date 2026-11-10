from __future__ import annotations

from typing import Any

from anomaly_reporting.templates import markdown_template


class ReportGenerator:
    def generate_markdown(
        self, engagement_name: str, findings: list[dict], context: dict[str, Any] | None = None
    ) -> str:
        return markdown_template(engagement_name, findings, context=context)

    def generate_html(
        self, engagement_name: str, findings: list[dict], context: dict[str, Any] | None = None
    ) -> str:
        md = self.generate_markdown(engagement_name, findings, context=context)
        return f"<html><body><pre>{md}</pre></body></html>"

    def generate_pdf(
        self, engagement_name: str, findings: list[dict], context: dict[str, Any] | None = None
    ) -> bytes:
        # Stub PDF bytes
        content = self.generate_markdown(engagement_name, findings, context=context)
        return content.encode("utf-8")
