from __future__ import annotations

from anomaly_reporting import ReportGenerator


def test_generate_markdown_and_html():
    gen = ReportGenerator()
    md = gen.generate_markdown(
        "Test", [{"title": "XSS", "severity": "high", "description": "desc"}]
    )
    assert "XSS" in md
    html = gen.generate_html("Test", [])
    assert "<html" in html
    pdf = gen.generate_pdf("Test", [])
    assert isinstance(pdf, bytes)
