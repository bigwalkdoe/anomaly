# Assessment Request Idempotency — Short Design

**Date:** 2026-11-28
**Scope:** bounded vertical-slice gap: best-effort idempotency for legacy and v1 assessment/run creation

## Intent

`BL-004` calls for best-effort idempotency on assessment requests. Today, replaying `POST /api/engagements/{id}/runs` or `POST /api/v1/engagements/{id}/runs` re-runs policy evaluation and enqueues another `Run`. This gap makes a client-supplied key reuse the first run instead of creating duplicates, without changing the existing response contract.

## Goals

- Accept an `Idempotency-Key` header on both legacy and v1 run creation.
- Scope keys to `(engagement, user)` so one caller cannot collide with another.
- Return the original run on replay without re-evaluating policy or enqueueing again.
- Preserve the existing `202 Accepted` response and run response fields.
- Record an engagement-scoped audit event for replay detection.

## Non-goals / anti-goals

- No full `assessment_requests` resource or persistent request/response snapshot.
- No cross-engagement or cross-user dedupe.
- No change to policy semantics, scope checks, scheduler dispatch, or playbook runs.
- No raw idempotency key in audit metadata or logs.

## Constraints

- Additive migration only; nullable column plus unique constraint so existing rows remain valid.
- Current Alembic head is `a1b2c3d4e5f6`; the new revision must depend on it.
- Legacy run routes currently lack `Request`; adding it is additive.
- v1 run routes already accept `Request` and return an envelope built from a run dict.
- All tenant/role checks remain in the existing `require_engagement_access` dependency.

## Approaches considered

1. **DB-backed unique hash (chosen).** Add `runs.idempotency_key_hash`, a nullable `String(64)` holding SHA-256 of the trimmed key, with a unique constraint on `(engagement_id, user_id, idempotency_key_hash)`. A pre-check finds replays; the unique constraint closes the concurrent-request race. Strong enough for production without a new domain resource.
2. **Params-only marker.** Store the key in `run.params` and query JSON before enqueue. Smallest diff and no migration, but not indexed, race-prone, and vulnerable to params rewriting. Rejected as too weak for a production-grade slice.
3. **Separate request table.** Add `assessment_requests` with key, fingerprint, state, and run link. Most extensible and auditable, but materially larger than this bounded gap; defer unless later lifecycle/idempotency needs justify it.

## Chosen design

- Normalize the header by trimming whitespace; reject empty or >255-character keys with `400` at the API boundary. Do not case-fold. The core helper raises a framework-neutral `InvalidIdempotencyKey(ValueError)` that routers translate to `400`.
- Hash the normalized key with SHA-256 and store only the digest. Scope uniqueness to `(engagement_id, user_id, digest)`.
- In both routers, after engagement access is enforced but before policy evaluation:
  - look up an existing run by engagement, user, and digest;
  - if found, emit `run.idempotent_replay` audit metadata containing the digest and run id, then return that run as `202`;
  - if not found, pass the digest into the shared enqueue helper so it is stored on the new run.
- Handle a unique-constraint race by rolling back and refetching the existing run, then following the replay path.
- Add `idempotent_replay: bool = False` to the legacy response model and the v1 run dict so replay is observable without breaking clients.
- Audit replay metadata uses `idempotency_key_hash`, never the raw key.

## What is left to the builder

- Write tests first for: legacy replay, v1 replay, blank/oversized key rejection, and concurrent-style duplicate handling through the shared helper.
- Implement the migration, model field, shared helper changes, and router wiring.
- Run the full test/lint/type gates, update `TASKS.md` and the SDD progress ledger, and commit/push the bounded gap.
