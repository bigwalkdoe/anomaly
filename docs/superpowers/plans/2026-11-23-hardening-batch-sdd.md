# Vertical Slice Hardening Batch (SDD)

> **For agentic workers:** Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add regression coverage and small hardening fixes for remaining governed vertical-slice gaps: runner/executor guardrails, evidence/report traceability consistency, and no-leak/min-role parity edges.

**Architecture:** Keep changes additive and consistent with existing patterns (`require_engagement_access`, `engagement_accessible`, shared assessment/enqueue flow, AuditService). Prefer tests first where practical; do not do destructive migration surgery.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, pytest/pytest-asyncio, Ruff.

## Global Constraints

- Preserve no-leak semantics: cross-tenant/non-member engagement-scoped resources return 404; known members with insufficient role return 403.
- Keep tenant scoping via `organization_id`/membership checks where applicable.
- Do not weaken policy-before-execution: worker/executor must re-validate policy/manifest before execution.
- Add/adjust tests for any behavior change; run targeted pytest and ruff on touched files.
- Do not modify Alembic migration history in this batch.

## File Map

- Modify: `apps/worker/src/anomaly_worker/executor.py` (only if test exposes gap)
- Test: `tests/core/test_executor_guardrails.py` (new)
- Modify: `apps/api/src/anomaly_api/routers/reports.py` or `packages/reporting/*` (only if gap found)
- Modify: `apps/api/src/anomaly_api/routers/evidence.py` (only if gap found)
- Test: `tests/api/test_evidence.py` / `tests/reporting/test_report_traceability.py` / `tests/api/test_tenancy_isolation.py` / `tests/api/test_rbac.py` (as needed)
- Modify: `TASKS.md` (progress note when batch complete)

### Task 1: Executor guardrail regression tests

**Files:**
- Create: `tests/core/test_executor_guardrails.py`
- Reference: `apps/worker/src/anomaly_worker/executor.py`

- [ ] **Step 1: Write failing/coverage tests**
  - Add test that `execute_run` fails with `RunStatus.failed`, `policy.denied` audit metadata reason `too_many_targets` when targets exceed `MAX_TARGETS_PER_RUN`.
  - Add test that stored evidence metadata includes `stdout_truncated`/`stderr_truncated` flags and truncates stored stdout/stderr while preserving full-content SHA-256 behavior.

- [ ] **Step 2: Run tests to verify**
  - Run: `python3 -m pytest -q tests/core/test_executor_guardrails.py`

- [ ] **Step 3: Minimal implementation if needed**
  - Only adjust executor if tests reveal a real gap.

- [ ] **Step 4: Verify**
  - Run: `python3 -m pytest -q tests/core/test_executor_guardrails.py`
  - Run: `python3 -m ruff check apps/worker/src/anomaly_worker/executor.py tests/core/test_executor_guardrails.py`

- [ ] **Step 5: Commit**
  - `git add ... && git commit -m "test(worker): cover executor guardrail limits and truncation"`

### Task 2: Evidence/report traceability consistency

**Files:**
- Modify/Test: `tests/api/test_evidence.py`, `tests/reporting/test_report_traceability.py`, `tests/api/test_reports.py` or existing report tests as appropriate
- Reference: `apps/api/src/anomaly_api/routers/evidence.py`, `apps/api/src/anomaly_api/routers/reports.py`, `apps/api/src/anomaly_api/routers/v1_slice.py`, `packages/reporting/`

- [ ] **Step 1: Inspect for gaps**
  - Confirm evidence download/integrity expose provenance consistently; confirm reports include org/engagement/job/execution/finding/evidence traceability in legacy and v1 generation paths.

- [ ] **Step 2: Write failing tests for any gap**
  - Add targeted tests only for real missing behavior.

- [ ] **Step 3: Implement minimal fix**
  - Keep API response shapes additive.

- [ ] **Step 4: Verify**
  - Run targeted pytest for touched evidence/report tests and ruff on touched files.

- [ ] **Step 5: Commit**
  - Commit focused changes.

### Task 3: No-leak/min-role parity sweep

**Files:**
- Modify/Test: `tests/api/test_rbac.py`, `tests/api/test_tenancy_isolation.py`, and any router needing fix
- Reference: `apps/api/src/anomaly_api/routers/*.py`

- [ ] **Step 1: Audit endpoints**
  - Scan for engagement/resource ID endpoints lacking consistent no-leak (404 for non-member/cross-tenant) or min-role enforcement.

- [ ] **Step 2: Add regression tests for concrete gaps**
  - Prefer extending existing tenancy/RBAC tests.

- [ ] **Step 3: Implement minimal fixes**
  - Use `require_engagement_access` or existing `engagement_accessible` patterns.

- [ ] **Step 4: Verify**
  - Run: `python3 -m pytest -q tests/api/test_rbac.py tests/api/test_tenancy_isolation.py` and any touched API tests; ruff on touched files.

- [ ] **Step 5: Commit**
  - Commit focused changes and update TASKS.md progress note.
