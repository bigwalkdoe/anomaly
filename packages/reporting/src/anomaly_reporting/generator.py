from __future__ import annotations

from anomaly_reporting.templates import markdown_template


class ReportGenerator:
    def generate_markdown(self, engagement_name: str, findings: list[dict]) -> str:
        return markdown_template(engagement_name, findings)

    def generate_html(self, engagement_name: str, findings: list[dict]) -> str:
        md = self.generate_markdown(engagement_name, findings)
        return f"<html><body><pre>{md}</pre></body></html>"

    def generate_pdf(self, engagement_name: str, findings: list[dict]) -> bytes:
        # Stub PDF bytes
        content = self.generate_markdown(engagement_name, findings)
        return content.encode("utf-8")
