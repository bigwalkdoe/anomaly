# Assessment Policy Decision Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record allow and deny assessment policy decisions with reason and scope context across assessment request paths.

**Architecture:** Add a JSON-safe metadata formatter to the core `PolicyDecision`, add a shared API audit recorder, and wire legacy/v1 run creation through it. Keep `policy.denied` for denials and add `policy.allowed` for allowed requests; reuse the formatter in manifests, scheduler, and executor audits so all decision records have consistent scope context.

**Tech Stack:** Python 3.x, FastAPI, SQLAlchemy async, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-11-27-assessment-policy-decision-traceability-design.md`

## Global Constraints

- Keep existing `policy.denied` audit action for denied decisions.
- Do not change approval/scope policy semantics.
- All audit metadata must be JSON-safe and include `allowed`, `reason`, and `op`.
- Scope metadata must be present whenever a `ScopeCheckResult` exists: `targets`, `in_scope`, `out_of_scope`, `has_warning`.
- Use TDD: write and run failing tests before implementation.
- Verification gate: tests in `tests/api tests/core tests/ai tests/tools tests/security`, `ruff check .`, `python3 -m mypy packages apps`.

## Review Focus

- Allowed requests with a scope result must not report an empty decision record: covered by the allowed-run audit test.
- Denied out-of-scope requests must retain `policy.denied` and expose the offending targets: covered by the out-of-scope audit test.
- Denied unapproved engagements must expose the engagement status even without scope data: covered by the unapproved audit test.
- V1 run creation must use the same recorder as legacy run creation: covered by the v1 audit test.
- Execution manifests must carry a real decision record rather than a hard-coded allow: covered by the manifest decision test.

---

### Task 1: Shared policy decision metadata

**Files:**
- Modify: `packages/core/src/anomaly_core/policy.py`
- Test: `tests/core/test_policy_decision_metadata.py`

**Interfaces:**
- Consumes: `PolicyDecision` and `ScopeCheckResult` from `anomaly_core.policy`/`anomaly_core.scope`.
- Produces: `PolicyDecision.to_metadata(*, op: str = "assessment.request", source: str | None = None) -> dict[str, Any]`.

- [x] **Step 1: Write failing tests for denied scope metadata, unapproved metadata, and allowed metadata**

```python
def test_decision_metadata_for_out_of_scope_includes_scope_context():
    decision = PolicyDecision(
        allowed=False,
        reason="out_of_scope",
        metadata={"targets": ["evil.test"]},
        scope_result=ScopeCheckResult(["allowed.test"], ["evil.test"], True),
    )
    metadata = decision.to_metadata(op="assessment.request")
    assert metadata["allowed"] is False
    assert metadata["reason"] == "out_of_scope"
    assert metadata["op"] == "assessment.request"
    assert metadata["out_of_scope"] == ["evil.test"]
    assert metadata["has_warning"] is True
```

- [x] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q tests/core/test_policy_decision_metadata.py`
Expected: FAIL with `AttributeError`/missing method.

- [x] **Step 3: Implement `PolicyDecision.to_metadata`**

Return a new dict combining existing metadata with `allowed`, `reason`, `op`, optional `source`, and scope fields when `scope_result` exists. Do not mutate the original `metadata`.

- [x] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q tests/core/test_policy_decision_metadata.py`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add packages/core/src/anomaly_core/policy.py tests/core/test_policy_decision_metadata.py
git commit -m "test: pin assessment policy decision metadata"
```

### Task 2: Record API assessment decisions

**Files:**
- Modify: `apps/api/src/anomaly_api/assessment.py`
- Modify: `apps/api/src/anomaly_api/routers/runs.py`
- Modify: `apps/api/src/anomaly_api/routers/v1_slice.py`
- Test: `tests/api/test_runs_policy.py`

**Interfaces:**
- Consumes: `PolicyDecision.to_metadata(...)` from Task 1.
- Produces: `record_assessment_policy_decision(db, user, engagement, decision, *, source, op="assessment.request") -> None`; `enforce_assessment_policy(..., source: str | None = None)`.

- [x] **Step 1: Write failing API tests**

```python
@pytest.mark.asyncio
async def test_allowed_assessment_records_policy_allowed_audit(client, db_session):
    # Seed approved engagement, in-scope target, pentester membership.
    response = await client.post(... json={"tool": "stub", "targets": ["allowed.test"]})
    assert response.status_code == 202
    log = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "policy.allowed")
    )
    assert log is not None
    assert log.metadata["allowed"] is True
    assert log.metadata["reason"] is None
    assert log.metadata["in_scope"] == ["allowed.test"]
```

Also add failing tests for denied out-of-scope metadata, denied unapproved metadata, and a v1 allowed run audit with `source` recorded.

- [x] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=apps/api/src:packages/core/src ... .venv/bin/python -m pytest -q tests/api/test_runs_policy.py`
Expected: FAIL with missing `policy.allowed` audit or missing scope metadata.

- [x] **Step 3: Implement the recorder and wire call sites**

Add `record_assessment_policy_decision` in `assessment.py`; call it from `enforce_assessment_policy` for both allowed and denied decisions. Pass `source="api.legacy"` from `runs.py` and `source="api.v1"` from `v1_slice.py`.

- [x] **Step 4: Run the tests to verify they pass**

Run: targeted `tests/api/test_runs_policy.py`.
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/api/src/anomaly_api/assessment.py apps/api/src/anomaly_api/routers/runs.py apps/api/src/anomaly_api/routers/v1_slice.py tests/api/test_runs_policy.py
git commit -m "feat: trace assessment policy decisions"
```

### Task 3: Reuse decision metadata in execution and scheduler audits

**Files:**
- Modify: `apps/api/src/anomaly_api/assessment.py`
- Modify: `packages/core/src/anomaly_core/scheduler.py`
- Modify: `apps/worker/src/anomaly_worker/executor.py`
- Test: `tests/core/test_scheduler_dispatch.py`, `tests/core/test_executor_guardrails.py`

**Interfaces:**
- Consumes: `PolicyDecision.to_metadata(...)` from Task 1.
- Produces: no new public interfaces.

- [x] **Step 1: Write failing assertions for scope context in existing denial audits**

Add assertions that scheduler and executor `policy.denied` metadata contain `allowed`, `reason`, `out_of_scope`, and `has_warning`. Add an assertion that the enqueued manifest's `execution_policy` contains `allowed` and `reason` from the decision formatter.

- [x] **Step 2: Run tests to verify they fail**

Run: targeted scheduler/executor tests.
Expected: FAIL with missing metadata keys.

- [x] **Step 3: Replace ad-hoc decision metadata and hard-coded manifests**

Use `decision.to_metadata(...)` in scheduler/executor denial audits and for manifest `policy_decision` in API enqueue and scheduler enqueue.

- [x] **Step 4: Run tests to verify they pass**

Run: targeted scheduler/executor tests.
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add apps/api/src/anomaly_api/assessment.py packages/core/src/anomaly_core/scheduler.py apps/worker/src/anomaly_worker/executor.py tests/core/test_scheduler_dispatch.py tests/core/test_executor_guardrails.py
git commit -m "refactor: reuse policy decision metadata"
```

### Task 4: Full verification and documentation

**Files:**
- Modify: `TASKS.md`
- Create: `.superpowers/sdd/2026-11-27-assessment-policy-decision-traceability/progress.md`

**Interfaces:**
- Consumes: completed implementation from Tasks 1–3.
- Produces: updated progress ledger.

- [x] **Step 1: Run full verification**

```bash
set -a && source .env && set +a && PYTHONPATH=apps/api/src:apps/worker/src:apps/cli/src:packages/core/src:packages/tools/src:packages/ai/src:packages/reporting/src:packages/integrations/src:packages/common/src .venv/bin/python -m pytest -q tests/api tests/core tests/ai tests/tools tests/security
ruff check .
python3 -m mypy packages apps
```

Expected: all tests pass; ruff clean; mypy clean.

- [x] **Step 2: Update progress documentation**

Append a TASKS.md progress entry with test/lint/type results and write the SDD progress checklist.

- [x] **Step 3: Commit and push**

```bash
git add TASKS.md docs/superpowers/specs/2026-11-27-assessment-policy-decision-traceability-design.md docs/superpowers/plans/2026-11-27-assessment-policy-decision-traceability.md
git commit -m "docs: record assessment policy traceability progress"
git push origin main
```
