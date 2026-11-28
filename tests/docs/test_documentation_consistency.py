from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_readiness_checklist_is_canonical_and_linked():
    readiness = _doc("docs/PRODUCTION_READINESS.md")

    for heading in (
        "## Release gates",
        "## Operational verification",
        "## Evidence commands",
        "## Known blockers",
        "## Sign-off",
    ):
        assert heading in readiness

    for token in (
        "Idempotency-Key",
        "ANOMALY_CORS_ORIGINS",
        "ANOMALY_METRICS_AUTH_REQUIRED",
        "MAX_UPLOAD_SIZE_BYTES",
        "Authorization: Bearer",
        "Content-Security-Policy",
        "ruff check .",
        "mypy packages apps",
        "alembic check",
        "pytest",
    ):
        assert token in readiness

    for path in ("README.md", "SECURITY.md", "docs/DEPLOYMENT_GUIDE.md"):
        assert "PRODUCTION_READINESS.md" in _doc(path)


def test_api_guide_documents_idempotency_and_v1_contract():
    api_guide = _doc("docs/API_GUIDE.md")

    assert "Idempotency-Key" in api_guide
    assert "idempotent_replay" in api_guide
    for token in ("success", "data", "meta", "request_id"):
        assert token in api_guide
    assert "token param or Authorization: Bearer header" in api_guide
    assert "Admin only" in api_guide
