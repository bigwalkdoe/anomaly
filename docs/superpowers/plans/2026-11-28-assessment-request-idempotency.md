# Assessment Request Idempotency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repeated legacy and v1 assessment requests with the same `Idempotency-Key` reuse the first run instead of enqueueing duplicates.

**Architecture:** Add a nullable hashed idempotency field to `runs` with a scoped unique constraint. Shared API helpers normalize/hash the header, find existing runs, emit replay audits, and handle unique-constraint races; routers call the helpers before policy evaluation and reuse the existing run on replay.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.x async, Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-11-28-assessment-request-idempotency-design.md`

## Global Constraints

- Additive migration only; nullable column plus unique constraint so existing rows remain valid.
- Current Alembic head is `a1b2c3d4e5f6`; the new revision must depend on it.
- Preserve `202 Accepted` for both new and replayed assessment requests.
- Scope keys to `(engagement_id, user_id)`, never across users or engagements.
- Store and audit only the SHA-256 digest of the key; never store or log the raw key.
- All tenant/role checks remain in the existing `require_engagement_access` dependency.
- Do not change policy semantics, scope checks, scheduler dispatch, playbook runs, or inline execution.

## Review Focus

- Blank or oversized `Idempotency-Key` → `400` and no run is created; Task 2 test `test_blank_and_oversized_idempotency_keys_are_rejected`.
- Same key retried by the same user on the same engagement → same run id, `202`, one enqueue/policy audit, one replay audit; Task 2 test `test_legacy_replay_reuses_run_and_audits_replay`.
- Same key from a different user or on a different engagement → separate runs; Task 2 test `test_idempotency_key_is_scoped_to_engagement_and_user`.
- Pre-check miss plus concurrent duplicate insert → existing run is returned and replay is audited; Task 2 test `test_duplicate_race_reuses_existing_run`.
- v1 replay → same reuse semantics inside the `success/data/meta` envelope with `data.idempotent_replay`; Task 3 test `test_v1_replay_reuses_run_in_envelope`.

---

### Task 1: Idempotency key primitives and run persistence

**Files:**
- Modify: `packages/core/src/anomaly_core/models/run.py`
- Create: `packages/core/alembic/versions/b2c3d4e5f6a7_add_run_idempotency_hash.py`
- Create: `packages/core/src/anomaly_core/assessment_idempotency.py`
- Test: `tests/core/test_assessment_idempotency.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `MAX_IDEMPOTENCY_KEY_LENGTH: int = 255`
  - `class InvalidIdempotencyKey(ValueError)`
  - `normalize_idempotency_key(raw: str | None) -> str | None` — returns `None` for absent header, strips whitespace, raises `InvalidIdempotencyKey` for blank or >255 chars. Routers translate it to `HTTPException(400)`.
  - `hash_idempotency_key(key: str) -> str` — lowercase hex SHA-256 digest.
  - `Run.idempotency_key_hash: Mapped[str | None]`.

- [ ] **Step 1: Write the failing pure tests**

Create `tests/core/test_assessment_idempotency.py` with these tests:

```python
def test_hash_idempotency_key_is_stable_sha256():
    from anomaly_core.assessment_idempotency import hash_idempotency_key

    digest = hash_idempotency_key("client-key")

    assert len(digest) == 64
    assert digest == "8eb943e7040b69a94bf39562088223755bff4c2e7c5fc257f1e08f870fe01d35"
```

```python
def test_normalize_idempotency_key_rejects_blank_and_oversized():
    import pytest
    from anomaly_core.assessment_idempotency import (
        MAX_IDEMPOTENCY_KEY_LENGTH,
        InvalidIdempotencyKey,
        normalize_idempotency_key,
    )

    assert normalize_idempotency_key(None) is None
    assert normalize_idempotency_key("  key-1  ") == "key-1"
    with pytest.raises(InvalidIdempotencyKey):
        normalize_idempotency_key("   ")
    with pytest.raises(InvalidIdempotencyKey):
        normalize_idempotency_key("x" * (MAX_IDEMPOTENCY_KEY_LENGTH + 1))
```

```python
def test_run_model_exposes_idempotency_hash():
    from anomaly_core.models import Run

    assert hasattr(Run, "idempotency_key_hash")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/core/test_assessment_idempotency.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'anomaly_core.assessment_idempotency'` and missing `Run.idempotency_key_hash`.

- [ ] **Step 3: Add the model field and unique constraint**

In `packages/core/src/anomaly_core/models/run.py`, import `UniqueConstraint` and add:

```python
__table_args__ = (
    UniqueConstraint(
        "engagement_id",
        "user_id",
        "idempotency_key_hash",
        name="uq_runs_engagement_user_idempotency",
    ),
)
```

Add `idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)` to `Run`. Keep all existing columns and relationships unchanged.

- [ ] **Step 4: Add the additive migration**

Create revision `b2c3d4e5f6a7`, `down_revision = "a1b2c3d4e5f6"`. The upgrade must:
- add `runs.idempotency_key_hash` as nullable `String(64)` if absent;
- create unique constraint `uq_runs_engagement_user_idempotency` on `(engagement_id, user_id, idempotency_key_hash)` if no equivalent constraint exists.

The downgrade must drop that constraint (if present) and then drop the column (if present). Follow the idempotent inspector guards used in `f2a3b4c5d6e7_add_org_to_tags.py`.

- [ ] **Step 5: Implement the pure helpers**

In `packages/core/src/anomaly_core/assessment_idempotency.py`:
- define `MAX_IDEMPOTENCY_KEY_LENGTH = 255` and `InvalidIdempotencyKey(ValueError)`;
- implement `normalize_idempotency_key(raw: str | None) -> str | None` using `InvalidIdempotencyKey` for invalid non-absent values;
- implement `hash_idempotency_key(key: str) -> str` with `hashlib.sha256(key.encode("utf-8")).hexdigest()`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `PYTHONPATH=packages/core/src .venv/bin/python -m pytest -q --noconftest tests/core/test_assessment_idempotency.py`
Expected: PASS (3 tests).

- [ ] **Step 7: Verify the migration graph**

Run: `/home/deon/dev/github/anomaly/.venv/bin/alembic heads` from `packages/core`.
Expected: exactly one head, `b2c3d4e5f6a7 (head)`.

- [ ] **Step 8: Commit**

```bash
git add packages/core/src/anomaly_core/models/run.py packages/core/alembic/versions/b2c3d4e5f6a7_add_run_idempotency_hash.py packages/core/src/anomaly_core/assessment_idempotency.py tests/core/test_assessment_idempotency.py
git commit -m "feat: persist assessment idempotency keys"
```

### Task 2: Shared idempotent enqueue and legacy API behavior

**Files:**
- Modify: `apps/api/src/anomaly_api/assessment.py`
- Modify: `apps/api/src/anomaly_api/routers/runs.py`
- Create: `tests/api/test_runs_idempotency.py`

**Interfaces:**
- Consumes: `normalize_idempotency_key`, `hash_idempotency_key` from Task 1; `enforce_assessment_policy`, `enqueue_assessment_run` from the existing API helper.
- Produces:
  - `@dataclass(frozen=True) class IdempotentRunResult: run: Run; replayed: bool`
  - `async def find_idempotent_run(db: AsyncSession, *, engagement_id: UUID, user_id: UUID, key_hash: str) -> Run | None`
  - `async def record_idempotent_replay(db: AsyncSession, *, user: User, engagement: Engagement, run: Run, key_hash: str) -> None`
  - `enqueue_assessment_run(..., idempotency_key_hash: str | None = None)` stores the hash on the new `Run`.
  - `async def enqueue_assessment_run_with_idempotency(db: AsyncSession, *, user: User, engagement: Engagement, tool: str, targets: list[str], idempotency_key_hash: str | None, policy_decision: PolicyDecision, params: dict[str, Any] | None = None) -> IdempotentRunResult`

- [ ] **Step 1: Write failing legacy API tests**

Create `tests/api/test_runs_idempotency.py`. Use a local `_seed_engagement(db, user_email)` helper that get-or-creates admin/pentester roles, creates owner and pentester users, an approved `Engagement`, `EngagementMember`, `Scope`, and one in-scope `ScopeEntry("allowed.test")`, commits, and returns `(pentester, engagement)`. Include these tests:

```python
@pytest.mark.asyncio
async def test_legacy_replay_reuses_run_and_audits_replay(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-replay@example.com")
    headers = {
        "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
        "Idempotency-Key": "client-key-1",
    }
    body = {"tool": "stub", "targets": ["allowed.test"]}

    first = await client.post(f"/api/engagements/{eng.id}/runs", headers=headers, json=body)
    second = await client.post(f"/api/engagements/{eng.id}/runs", headers=headers, json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["idempotent_replay"] is True
    runs = (await db_session.scalars(select(Run).where(Run.engagement_id == eng.id))).all()
    assert len(runs) == 1
    enqueues = (await db_session.scalars(select(AuditLog).where(AuditLog.action == "run.enqueue"))).all()
    assert len(enqueues) == 1
    replay = await db_session.scalar(select(AuditLog).where(AuditLog.action == "run.idempotent_replay"))
    assert replay is not None
    assert replay.metadata["idempotency_key_hash"] == "64dbdc38ede19b85cac8beccc15d52debb1a30e42c2fa15716ce95ac0913ad09"
    assert "client-key-1" not in str(replay.metadata)
```

```python
@pytest.mark.asyncio
async def test_blank_and_oversized_idempotency_keys_are_rejected(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-invalid-key@example.com")
    base = {"Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}"}
    body = {"tool": "stub", "targets": ["allowed.test"]}

    blank = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={**base, "Idempotency-Key": "   "},
        json=body,
    )
    oversized = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={**base, "Idempotency-Key": "x" * 256},
        json=body,
    )

    assert blank.status_code == 400
    assert oversized.status_code == 400
    assert (await db_session.scalar(select(func.count()).select_from(Run))) == 0
```

```python
@pytest.mark.asyncio
async def test_idempotency_key_is_scoped_to_engagement_and_user(client, db_session):
    pt, eng = await _seed_engagement(db_session, "legacy-scope@example.com")
    pt2, eng2 = await _seed_engagement(db_session, "legacy-scope-2@example.com")
    db_session.add(EngagementMember(engagement_id=eng2.id, user_id=pt.id, role=RoleName.pentester))
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=pt2.id, role=RoleName.pentester))
    await db_session.commit()
    body = {"tool": "stub", "targets": ["allowed.test"]}

    first = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )
    other_eng = await client.post(
        f"/api/engagements/{eng2.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )
    other_user = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers={
            "Authorization": f"Bearer {create_access_token(pt2.id, ['pentester'])}",
            "Idempotency-Key": "same-key",
        },
        json=body,
    )

    assert first.status_code == 202
    assert other_eng.status_code == 202
    assert other_user.status_code == 202
    assert len({first.json()["id"], other_eng.json()["id"], other_user.json()["id"]}) == 3
```

```python
@pytest.mark.asyncio
async def test_duplicate_race_reuses_existing_run(client, db_session, monkeypatch):
    pt, eng = await _seed_engagement(db_session, "legacy-race@example.com")
    key_hash = "4d417b736472e804fd99a8689e537b9a15ab0ea5b048683ffeb577bc6ef3e586"
    headers = {
        "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
        "Idempotency-Key": "race-key",
    }
    first = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )
    existing = await db_session.scalar(
        select(Run).where(Run.idempotency_key_hash == key_hash)
    )
    real_find = anomaly_api.assessment.find_idempotent_run
    calls = 0

    async def miss_then_find(*args, **kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_find(*args, **kwargs)

    monkeypatch.setattr(anomaly_api.assessment, "find_idempotent_run", miss_then_find)

    replay = await client.post(
        f"/api/engagements/{eng.id}/runs",
        headers=headers,
        json={"tool": "stub", "targets": ["allowed.test"]},
    )

    assert first.status_code == 202
    assert replay.status_code == 202
    assert replay.json()["id"] == str(existing.id)
    assert replay.json()["idempotent_replay"] is True
    assert calls == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `bash -c 'set -a; source .env; set +a; PYTHONPATH=apps/api/src:apps/worker/src:packages/core/src:packages/tools/src:packages/ai/src .venv/bin/python -m pytest -q tests/api/test_runs_idempotency.py'`
Expected: FAIL because the idempotency helpers and `idempotent_replay` response field do not exist.

- [ ] **Step 3: Implement shared helpers**

In `apps/api/src/anomaly_api/assessment.py`:
- import `IntegrityError` from `sqlalchemy.exc`, `dataclass`, and the Task 1 helpers;
- add `IdempotentRunResult`;
- implement `find_idempotent_run` with `select(Run).where(Run.engagement_id == ..., Run.user_id == ..., Run.idempotency_key_hash == ...)`;
- implement `record_idempotent_replay` using `AuditService.log(action="run.idempotent_replay", resource_type="run", resource_id=run.id, engagement_id=engagement.id, organization_id=engagement.organization_id, metadata={"idempotency_key_hash": key_hash, "run_id": str(run.id)})` followed by `db.commit()`;
- add `idempotency_key_hash` to `enqueue_assessment_run` and assign it to `Run`;
- implement `enqueue_assessment_run_with_idempotency`: call `enqueue_assessment_run(..., commit=False, idempotency_key_hash=key_hash)`, then commit/refresh; on `IntegrityError`, roll back, call `find_idempotent_run`, call `record_idempotent_replay`, and return `IdempotentRunResult(existing, True)`.

When `idempotency_key_hash` is `None`, the wrapper must simply enqueue with no idempotency audit and return `replayed=False`.

- [ ] **Step 4: Wire the legacy route**

In `apps/api/src/anomaly_api/routers/runs.py`:
- add `Request` to imports and `request: Request` to `create_run`;
- call shared helpers through the `assessment` module namespace (`from anomaly_api import assessment`) so lookup can be patched in the race test;
- normalize/hash `request.headers.get("idempotency-key")` before policy evaluation, translating `InvalidIdempotencyKey` to `HTTPException(status_code=400, detail=...)`;
- if a matching run exists, call `record_idempotent_replay` and return it immediately;
- otherwise evaluate policy and call `enqueue_assessment_run_with_idempotency`;
- add `idempotent_replay: bool = False` to `RunResponse` and include the wrapper result in the response.

Replay responses keep `202`; do not re-run `inline_execution_enabled()` on replay.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `bash -c 'set -a; source .env; set +a; PYTHONPATH=apps/api/src:apps/worker/src:packages/core/src:packages/tools/src:packages/ai/src .venv/bin/python -m pytest -q tests/api/test_runs_idempotency.py'`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/anomaly_api/assessment.py apps/api/src/anomaly_api/routers/runs.py tests/api/test_runs_idempotency.py
git commit -m "feat: add legacy assessment idempotency"
```

### Task 3: v1 API parity

**Files:**
- Modify: `apps/api/src/anomaly_api/routers/v1_slice.py`
- Modify: `tests/api/test_runs_idempotency.py`

**Interfaces:**
- Consumes: all helpers from Task 2.
- Produces: no new public interfaces.

- [ ] **Step 1: Write the failing v1 test**

Append to `tests/api/test_runs_idempotency.py`:

```python
@pytest.mark.asyncio
async def test_v1_replay_reuses_run_in_envelope(client, db_session):
    pt, eng = await _seed_engagement(db_session, "v1-replay@example.com")
    headers = {
        "Authorization": f"Bearer {create_access_token(pt.id, ['pentester'])}",
        "Idempotency-Key": "v1-client-key",
    }
    body = {"tool": "stub", "targets": ["allowed.test"], "params": {}}

    first = await client.post(f"/api/v1/engagements/{eng.id}/runs", headers=headers, json=body)
    second = await client.post(f"/api/v1/engagements/{eng.id}/runs", headers=headers, json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["success"] is True
    assert second.json()["data"]["id"] == first.json()["data"]["id"]
    assert second.json()["data"]["idempotent_replay"] is True
    runs = (await db_session.scalars(select(Run).where(Run.engagement_id == eng.id))).all()
    assert len(runs) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash -c 'set -a; source .env; set +a; PYTHONPATH=apps/api/src:apps/worker/src:packages/core/src:packages/tools/src:packages/ai/src .venv/bin/python -m pytest -q tests/api/test_runs_idempotency.py::test_v1_replay_reuses_run_in_envelope'`
Expected: FAIL because v1 creates two runs and has no `idempotent_replay` field.

- [ ] **Step 3: Wire the v1 route**

In `v1_create_run`, mirror the legacy flow using the shared helpers through the `assessment` module namespace:
- normalize/hash the header before policy evaluation, translating `InvalidIdempotencyKey` to `HTTPException(status_code=400, detail=...)`;
- replay existing run immediately with `record_idempotent_replay`;
- otherwise call `enqueue_assessment_run_with_idempotency`;
- include `idempotent_replay` in the `_envelope` data dict;
- do not re-run inline execution on replay.

- [ ] **Step 4: Run the idempotency tests to verify they pass**

Run: `bash -c 'set -a; source .env; set +a; PYTHONPATH=apps/api/src:apps/worker/src:packages/core/src:packages/tools/src:packages/ai/src .venv/bin/python -m pytest -q tests/api/test_runs_idempotency.py'`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/anomaly_api/routers/v1_slice.py tests/api/test_runs_idempotency.py
git commit -m "feat: add v1 assessment idempotency"
```

### Task 4: Full verification and documentation

**Files:**
- Modify: `TASKS.md`
- Create/update: `.superpowers/sdd/2026-11-28-assessment-request-idempotency/progress.md`

**Interfaces:**
- Consumes: completed implementation from Tasks 1–3.
- Produces: updated progress ledger and verified integration.

- [ ] **Step 1: Run full verification**

```bash
set -a && source .env && set +a && PYTHONPATH=apps/api/src:apps/worker/src:apps/cli/src:packages/core/src:packages/tools/src:packages/ai/src:packages/reporting/src:packages/integrations/src:packages/common/src .venv/bin/python -m pytest -q tests/api tests/core tests/ai tests/tools tests/security
ruff check .
python3 -m mypy packages apps
```

Expected: all tests pass; ruff clean; mypy clean.

- [ ] **Step 2: Update progress documentation**

Append a `TASKS.md` progress entry with the implementation summary and exact test/lint/type results. Record rulings and checklist completion in the SDD progress ledger.

- [ ] **Step 3: Commit and push**

```bash
git add TASKS.md docs/superpowers/specs/2026-11-28-assessment-request-idempotency-design.md docs/superpowers/plans/2026-11-28-assessment-request-idempotency.md
git commit -m "docs: record assessment idempotency progress"
git push origin main
```

Expected: `main` is aligned with `origin/main` and the working tree is clean.
