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


def test_current_baseline_docs_are_not_stale():
    tasks = _doc("TASKS.md")
    readme = _doc("README.md")
    security = _doc("SECURITY.md")
    deployment = _doc("docs/DEPLOYMENT_GUIDE.md")

    assert "_Last updated: 2026-11-28" in tasks
    assert "Current Alembic head: `b2c3d4e5f6a7`" in tasks
    assert "Organization/Workspace foundation exists" in readme

    for token in (
        "ANOMALY_METRICS_AUTH_REQUIRED",
        "MAX_UPLOAD_SIZE_BYTES",
        "PRODUCTION_READINESS.md",
    ):
        assert token in security

    for token in (
        "ANOMALY_CORS_ORIGINS",
        "ANOMALY_METRICS_AUTH_REQUIRED",
        "MAX_UPLOAD_SIZE_BYTES",
        "RUNNER_MODE",
        "NEXT_PUBLIC_API_URL",
    ):
        assert token in deployment


def test_production_config_docs_warn_about_ignored_and_default_settings():
    deployment = _doc("docs/DEPLOYMENT_GUIDE.md")
    readiness = _doc("docs/PRODUCTION_READINESS.md")
    readme = _doc("README.md")

    assert "CORS_ORIGINS is not read by the API" in deployment
    assert "ANOMALY_RUNNER=docker" in deployment
    assert "ANOMALY_RUNNER=docker" in readiness
    assert "pytest -q tests/api tests/core tests/ai tests/tools tests/security tests/docs" in readme
