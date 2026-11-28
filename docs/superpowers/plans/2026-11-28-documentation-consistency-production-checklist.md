# Documentation Consistency and Production Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one evidence-backed production readiness checklist and remove stale/incomplete facts from the repository's main docs.

**Architecture:** Add a canonical `docs/PRODUCTION_READINESS.md` release gate, link it from the main operator docs, refine the existing guides in place, and pin the required facts with a pure docs consistency test.

**Tech Stack:** Markdown, pytest with `pathlib`, existing repo test/lint/type gates

**Spec:** `docs/superpowers/specs/2026-11-28-documentation-consistency-production-checklist-design.md`

## Global Constraints

- Documentation only, plus one pure docs test; no product code or migration changes.
- Current Alembic head is `b2c3d4e5f6a7`; state it explicitly as the current baseline.
- Python floor is 3.12+ per `pyproject.toml` and CI; do not change it.
- Preserve the pre-production posture in `README.md`; the checklist is a gate, not a declaration.
- Historical `TASKS.md` progress entries are history; add a current-baseline note rather than rewriting them.
- Checklist gates must name concrete evidence commands, settings, or observable behavior.
- Full verification includes `tests/docs` in addition to the existing test directories.

## Review Focus

- Stale Alembic head could mislead an operator → Task 3 test `test_current_baseline_docs_are_not_stale`.
- Production checklist exists but is not discoverable from the main entry docs → Task 1 test `test_production_readiness_checklist_is_canonical_and_linked`.
- API guide omits `Idempotency-Key` or v1 envelope behavior → Task 2 test `test_api_guide_documents_idempotency_and_v1_contract`.
- Deployment env table omits security controls already implemented → Task 3 test `test_current_baseline_docs_are_not_stale`.
- Docs drift returns after this gap → all three tests remain in the full pytest suite.

---

### Task 1: Canonical production readiness checklist

**Files:**
- Create: `tests/docs/test_documentation_consistency.py`
- Create: `docs/PRODUCTION_READINESS.md`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `docs/DEPLOYMENT_GUIDE.md`

**Interfaces:**
- Consumes: existing repo layout and shipped controls documented in `README.md`, `SECURITY.md`, and `docs/DEPLOYMENT_GUIDE.md`.
- Produces:
  - `docs/PRODUCTION_READINESS.md` with sections `## Release gates`, `## Operational verification`, `## Evidence commands`, `## Known blockers`, and `## Sign-off`.
  - `tests/docs/test_documentation_consistency.py` helper `_doc(path: str) -> str` used by later tasks.

- [x] **Step 1: Write the failing canonical-link test**

Create `tests/docs/test_documentation_consistency.py`:

```python
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
```

- [x] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py::test_production_readiness_checklist_is_canonical_and_linked`

Expected: FAIL because `docs/PRODUCTION_READINESS.md` does not exist.

- [x] **Step 3: Create the canonical checklist**

Create `docs/PRODUCTION_READINESS.md`. Include exactly the five required section headings. Under `Release gates`, use checkboxes grouped as: code/quality gates, migration/data gates, security/config gates, execution/evidence gates, and release sign-off. Each gate must state its evidence, including the exact command or setting names required by the test. Under `Known blockers`, keep the platform explicitly pre-production until the remaining hardening in `README.md` is completed. Under `Sign-off`, require named release owner, evidence links, date, and residual-risk acceptance.

- [x] **Step 4: Add discoverability links**

- In `README.md`, add `- [Production Readiness Checklist](docs/PRODUCTION_READINESS.md)` to the Documentation list.
- In `SECURITY.md`, replace the top of the `## Production Checklist` section with a link to `docs/PRODUCTION_READINESS.md` and a short summary that points to the canonical gate.
- In `docs/DEPLOYMENT_GUIDE.md`, add a sentence near the top linking `[Production Readiness Checklist](PRODUCTION_READINESS.md)` before deploying beyond local development.

- [x] **Step 5: Run the docs test to verify it passes**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py::test_production_readiness_checklist_is_canonical_and_linked`

Expected: PASS.

- [x] **Step 6: Lint the touched test**

Run: `ruff check tests/docs/test_documentation_consistency.py`

Expected: All checks passed.

- [x] **Step 7: Commit**

```bash
git add tests/docs/test_documentation_consistency.py docs/PRODUCTION_READINESS.md README.md SECURITY.md docs/DEPLOYMENT_GUIDE.md
git commit -m "docs: add production readiness checklist"
```

### Task 2: API guide contract consistency

**Files:**
- Modify: `docs/API_GUIDE.md`
- Modify: `tests/docs/test_documentation_consistency.py`

**Interfaces:**
- Consumes: `_doc(path: str) -> str` from Task 1.
- Produces: no new interfaces.

- [x] **Step 1: Append the failing API guide test**

Append to `tests/docs/test_documentation_consistency.py`:

```python
def test_api_guide_documents_idempotency_and_v1_contract():
    api_guide = _doc("docs/API_GUIDE.md")

    assert "Idempotency-Key" in api_guide
    assert "idempotent_replay" in api_guide
    for token in ("success", "data", "meta", "request_id"):
        assert token in api_guide
    assert "token param or Authorization: Bearer header" in api_guide
    assert "Admin only" in api_guide
```

- [x] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py::test_api_guide_documents_idempotency_and_v1_contract`

Expected: FAIL because the API guide lacks idempotency and v1 envelope documentation.

- [x] **Step 3: Update the API guide**

In `docs/API_GUIDE.md`:
- add an `Idempotency-Key` paragraph under Runs: optional on `POST /api/engagements/{id}/runs`, trimmed, 1–255 chars, invalid values return `400`, replay returns the original run with `202` and `idempotent_replay: true`;
- add a v1 contract subsection stating additive `/api/v1` responses use `{"success": true, "data": ..., "meta": {"request_id": ...}}`, including `data.idempotent_replay` on run creation;
- change the WebSocket auth table text to `Yes (token param or Authorization: Bearer header)` for both WS rows;
- mark `GET /api/tags` and `POST /api/tags` as `Admin only`;
- state that `/api/metrics` may require admin auth when `ANOMALY_METRICS_AUTH_REQUIRED` is enabled.

- [x] **Step 4: Run the docs tests to verify they pass**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py`

Expected: PASS (2 tests).

- [x] **Step 5: Commit**

```bash
git add docs/API_GUIDE.md tests/docs/test_documentation_consistency.py
git commit -m "docs: align API guide with shipped contracts"
```

### Task 3: Current-baseline and deployment consistency

**Files:**
- Modify: `TASKS.md`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `docs/DEPLOYMENT_GUIDE.md`
- Modify: `tests/docs/test_documentation_consistency.py`

**Interfaces:**
- Consumes: `_doc(path: str) -> str` from Task 1.
- Produces: no new interfaces.

- [x] **Step 1: Append the failing baseline test**

Append to `tests/docs/test_documentation_consistency.py`:

```python
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
```

- [x] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py::test_current_baseline_docs_are_not_stale`

Expected: FAIL on the stale `TASKS.md` last-updated line and current head baseline.

- [x] **Step 3: Update the current baseline in TASKS.md**

- change the `_Last updated:` line to `2026-11-28 (assessment request idempotency, docs consistency, production readiness)`;
- add a `Current baseline:` line directly below it containing `Current Alembic head: \`b2c3d4e5f6a7\`` and the full verification command set: `ruff check .`, `python3 -m mypy packages apps`, and the pytest target list including `tests/docs`;
- leave historical progress entries intact.

- [x] **Step 4: Refine README current state**

In `README.md`:
- update the tenancy Known gap to say `Organization/Workspace foundation exists, but consistent server-side enforcement across every API, WebSocket, export, and worker surface is still incomplete`;
- update governed execution, evidence/reporting, and production-hardening bullets to reflect that the named controls are shipped in supported flows but full coverage/hardening remains;
- add the production readiness checklist to the Documentation list if Task 1's link is not already present.

- [x] **Step 5: Expand SECURITY.md checklist summary**

In the `## Production Checklist` section, keep the canonical link and add checkbox summary items naming `ANOMALY_METRICS_AUTH_REQUIRED`, `MAX_UPLOAD_SIZE_BYTES`, WS `Authorization: Bearer` preference, and evidence links in the canonical checklist.

- [x] **Step 6: Expand DEPLOYMENT_GUIDE.md environment table**

Add rows for `ANOMALY_CORS_ORIGINS` / `CORS_ALLOW_ORIGINS`, `ANOMALY_METRICS_AUTH_REQUIRED`, `MAX_UPLOAD_SIZE_BYTES`, `ANOMALY_RUNNER`, `ANOMALY_RUNNER_NETWORK`, `RUNNER_MODE` / `ANOMALY_INLINE_RUNS` (dev/test only), `NEXT_PUBLIC_API_URL`, and the production secret values from `.env.example`. Mark `RUNNER_MODE` and `ANOMALY_INLINE_RUNS` as never-for-production.

- [x] **Step 7: Run the docs tests to verify they pass**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs/test_documentation_consistency.py`

Expected: PASS (3 tests).

- [x] **Step 8: Commit**

```bash
git add TASKS.md README.md SECURITY.md docs/DEPLOYMENT_GUIDE.md tests/docs/test_documentation_consistency.py
git commit -m "docs: refresh current baseline and deployment facts"
```

### Task 4: Full verification and progress ledger

**Files:**
- Modify: `TASKS.md`
- Create/update: `.superpowers/sdd/2026-11-28-documentation-consistency-production-checklist/progress.md`

**Interfaces:**
- Consumes: completed docs and tests from Tasks 1–3.
- Produces: updated progress ledger and verified integration.

- [x] **Step 1: Run targeted docs tests**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/docs`

Expected: PASS (3 tests).

- [x] **Step 2: Run full verification**

```bash
set -a && source .env && set +a && PYTHONPATH=apps/api/src:apps/worker/src:apps/cli/src:packages/core/src:packages/tools/src:packages/ai/src:packages/reporting/src:packages/integrations/src:packages/common/src .venv/bin/python -m pytest -q tests/api tests/core tests/ai tests/tools tests/security tests/docs
ruff check .
python3 -m mypy packages apps
```

Expected: all tests pass; ruff clean; mypy clean. Record the exact counts in the ledger.

- [x] **Step 3: Verify migration graph still has one head**

Run: `/home/deon/dev/github/anomaly/.venv/bin/alembic heads` from `packages/core`.

Expected: exactly one head, `b2c3d4e5f6a7 (head)`.

- [x] **Step 4: Update progress documentation**

Append a `TASKS.md` progress entry with the implementation summary and exact test/lint/type results. Record approach rulings, test results, and checklist completion in the SDD progress ledger.

- [x] **Step 5: Commit and push**

```bash
git add TASKS.md docs/superpowers/specs/2026-11-28-documentation-consistency-production-checklist-design.md docs/superpowers/plans/2026-11-28-documentation-consistency-production-checklist.md
git commit -m "docs: record documentation consistency progress"
git push origin main
```

Expected: `main` is aligned with `origin/main` and the working tree is clean.
