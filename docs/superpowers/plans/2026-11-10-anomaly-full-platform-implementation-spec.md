# Anomaly Full Platform — Implementation Specification & Prioritized Backlog

**Date:** 2026-11-10  
**Status:** Draft (executable specification for incremental delivery)  
**Inputs:** `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md` (ADRs 001–012), `docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md`  
**Scope of this spec:** First production-grade governed vertical slice + prioritized backlog to close remaining blueprint gaps. All changes are **additive/incremental** and must preserve existing working functionality.

## 1. Objectives and acceptance

### 1.1 First vertical slice (end-to-end)
Deliver a governed flow with auditable controls and traceability:

1. **Authenticate** (identity + membership/permissions loaded)
2. **Create engagement** (scope + exclusions recorded)
3. **Approval** (request/decision recorded, auditable)
4. **Request assessment/run** (policy validates authorization + scope before execution)
5. **Isolated execution** (worker/runner performs approved operation in constrained environment)
6. **Normalize results** (findings stored and associated to engagement/assets/targets as applicable)
7. **Preserve evidence** (provenance + integrity metadata recorded)
8. **Generate traceable report** (linked to organization/engagement/job/run/execution context)

### 1.2 Mandatory security/test focus (must be covered)
- Cross-tenant authorization regression (tenant boundary enforced; no client-trusted org context)
- Runner isolation / scope-enforcement bypass (policy-before-exec, resolved-destination checks, containment limits)
- AI tool-execution policy bypass (AI remains advisory; no implicit execution permissions)
- Evidence integrity failure (checksums/provenance/access controls)
- Report traceability failure (report inputs/outputs linked to tenant, engagement, job/run, evidence)

## 2. Domain and data model changes (additive migrations)

> Implement in small migrations with backfills/defaults; no destructive drops. Enforce tenant ownership on all tenant-scoped records.

### 2.1 Tenancy (ADR-010, ADR-002)
**New/extended tables (proposed):**
- `organizations(id, name, slug, status, created_at, updated_at)`
- `workspaces(id, organization_id FK, name, slug, created_at, updated_at)` *(optional in phase 1; may start org-only)*
- `memberships(id, organization_id FK, user_id FK, role, status, created_at, updated_at)` *(evolve existing engagement_membership model carefully; keep backward compat)*

**Required propagation (phase 1 minimum):** add nullable `organization_id` to `engagements` (and derived linkage for scope/targets/runs/findings/evidence/reports/jobs where applicable), backfill, then enforce non-null + FKs + indexes. Tenant context derived server-side from authenticated membership.

**Files/migrations:**
- `packages/core/src/anomaly_core/models/organization.py` (new), updates to `engagement.py`, `membership.py`, `__init__.py`
- `packages/core/alembic/versions/<rev>_add_organizations_tenancy.py`
- Repository/service helpers: `packages/core/src/anomaly_core/tenancy.py` (new) for tenant scoping

### 2.2 Approvals and policy decisions (ADR-009, ADR-003)
- `approvals(id, organization_id, engagement_id, resource_type, resource_id, status[pending/approved/rejected/expired], requested_by, decided_by, reason, decided_at, expires_at, created_at)`
- `policy_decisions(id, organization_id, engagement_id, subject_type, subject_id, action, effect[allow/deny], reasons/json, evaluated_at, actor_id, correlation_id)`
- Engagement lifecycle extension (additive): support `pending_approval`/`approved`/`completed`/`archived` states as needed for slice while mapping existing statuses compatibly.

**Files/migrations:**
- `packages/core/src/anomaly_core/models/approval.py` (extend), `policy.py` (new) or extend existing
- `packages/core/alembic/versions/<rev>_add_approvals_policy_decisions.py`

### 2.3 Jobs/executions and run traceability (ADR-006, ADR-007, ADR-013/014 style events)
- Ensure runs/jobs carry: `organization_id`, `engagement_id`, `requested_by`, `approved_scope_ref/version`, `policy_decision_id`, `correlation_id`, `idempotency_key` (where applicable), state transitions, timestamps, error classification.
- `job_state_transitions` or append-only audit events for lifecycle: `created/validating/awaiting_approval/queued/running/collecting/completed/failed/cancelled`.

**Files/migrations:**
- Extend `packages/core/src/anomaly_core/models/run.py` (and/or introduce `jobs/executions` tables if separating)
- `packages/core/alembic/versions/<rev>_run_traceability_and_state.py`

### 2.4 Evidence integrity and provenance (ADR-011, gap §3.8)
- Evidence fields (additive): `organization_id`, `engagement_id`, `job_id/run_id`, `execution_id`, `finding_id` (nullable), `asset_id` (nullable), `collector_identity`, `tool_name`, `tool_version`, `storage_uri/key`, `sha256`, `content_type`, `size_bytes`, `classification`, `retention_policy`, `created_at`, immutable provenance metadata JSON.
- Enforce checksum verification on write/finalize; record access events.

**Files/migrations:**
- Extend `packages/core/src/anomaly_core/models/finding.py` (Evidence) or dedicated evidence model/module
- `packages/core/alembic/versions/<rev>_evidence_integrity_provenance.py`

### 2.5 Reports traceability (ADR-011, gap §3.9)
- Report records/artifacts linked to `organization_id`, `engagement_id`, `job/run ids`, evidence/finding set refs, template/version, generated_by, checksum, created_at.

**Files/migrations:**
- Extend reporting models/storage metadata as applicable
- `packages/core/alembic/versions/<rev>_report_traceability.py`

## 3. Service/API contracts (first slice)

### 3.1 Authentication & tenant context
- **Behavior:** resolve user, memberships, effective permissions, and active organization context server-side. Reject client-supplied org identifiers that do not match authorized membership.
- **Endpoints (existing/adjust):** `POST /api/auth/login`, token refresh/verify; add org selection/context if needed (e.g. `GET /api/me`, `GET /api/organizations`).
- **Acceptance:** cross-tenant access returns 403/404 without leaking existence per policy; all tenant-owned queries scoped by `organization_id`.

### 3.2 Engagement + scope
- **Endpoints:** existing `POST/GET /api/engagements`, scope/targets endpoints; enforce tenant ownership and lifecycle rules.
- **Contracts:** scope entries (in/out), exclusions, target validation; scope snapshot/version referenced by runs.

### 3.3 Approval workflow
- **Endpoints (proposed):**
  - `POST /api/engagements/{engagement_id}/approvals` (request)
  - `POST /api/approvals/{approval_id}/decision` (approve/reject; authorized roles only)
  - `GET /api/approvals` (scoped, filterable)
- **Audit:** emit audit events for request/decision with actor, reason, timestamps.

### 3.4 Policy-gated assessment/run request
- **Endpoint:** `POST /api/engagements/{engagement_id}/runs` (existing) — **must** perform: authz check, engagement/approval/state check, scope validation against resolved targets, policy decision recording, then enqueue authorized manifest only.
- **Response:** run/job id, status, policy decision ref, scope warnings/denials (explicit).
- **AI constraint:** `POST /api/ai/suggest-tools` and drafts remain advisory/audited; **no execution side effects**.

### 3.5 Execution/worker/runner boundary
- **Manifest (internal contract):** `job_id, organization_id, engagement_id, run_id, tool, tool_version, scope_ref, targets, params, limits(timeout/cpu/mem/pids), output/evidence destination, correlation_id, expires_at`.
- **Runner requirements:** no unrestricted platform credentials; scoped storage access; network/resource limits per profile; normalize outputs; record exit/error class; never execute in API process.
- **Worker:** claim/idempotent processing, state transitions, retries only for safe/transient failures.

### 3.6 Findings normalization and evidence
- **Endpoints:** existing findings/evidence/upload routes; ensure linkage to tenant/engagement/run and integrity metadata.
- **Contract:** evidence finalize/write computes/stores `sha256`; retrieval authorized and audited.

### 3.7 Reporting
- **Endpoint:** existing reports generation; output must reference tenant+engagement+run/job+evidence set and include provenance metadata in report artifact/record.
- **Formats:** at least one verifiable format in slice (JSON/Markdown/HTML/PDF as feasible) with traceability fields.

## 4. Event contracts (versioned, slice-relevant)
Emit via transactional outbox where feasible; include `event_id, event_type, schema_version, occurred_at, organization_id, engagement_id, correlation_id, actor_id?, payload`.

Minimum events: `engagement.created`, `engagement.approval.requested`, `engagement.approval.decided`, `policy.evaluated` (allow/deny), `run.requested`, `run.queued`, `run.started`, `run.completed|run.failed|run.cancelled`, `evidence.collected`, `finding.created|updated`, `report.generated`.

## 5. Security controls (implementation requirements)
- Centralized authorization at service/data-access layer (APIs, WS, exports, workers); admin `*` semantics preserved but tenant-scoped.
- Scope enforcement on resolved destinations (DNS/IP normalization considerations) with deny-by-policy for out-of-scope/expired approvals.
- Runner hardening baseline (no-new-privileges, drop caps, read-only where possible, limits, no docker socket/host mounts); profiles per ADR-007.
- Evidence checksums (SHA-256) and immutable provenance fields; authorized access logging.
- Structured audit logging for sensitive actions (auth, approvals, policy decisions, run lifecycle, evidence/report access).
- Secrets never logged; CORS/origins and session/CSRF posture tightened per environment (follow-up hardening acceptable if documented).

## 6. Observability and operations
- Correlation/request IDs propagated API → worker → runner → events.
- Structured logs for lifecycle and policy decisions; metrics for queue depth, run outcomes, policy denials, auth failures.
- Health/readiness endpoints remain; add checks for queue/storage dependencies as applicable.

## 7. Test plan (slice gates)
Automated tests (required for merge of slice components):
- **Authz/tenancy:** cross-org read/write denied for engagements, runs, findings, evidence, reports, approvals (API and service layer).
- **Approvals/policy:** run cannot execute without required approval/policy allow; denials audited.
- **Scope enforcement:** out-of-scope targets denied/warned per policy with recorded decision; no silent expansion.
- **Runner boundary:** execution invoked via worker/runner interface (not API inline in production path); manifest contains scoped context; limits applied (unit/integration with fakes where needed).
- **AI safety:** suggest/draft endpoints produce no run execution and are audited.
- **Evidence integrity:** checksum stored/verified; provenance fields present and linked.
- **Report traceability:** generated report references org/engagement/run/evidence identifiers.

Verification commands (local/CI): `ruff check .`, `mypy packages apps`, `pytest -q` (or split CI jobs), web lint/build, Alembic upgrade on clean DB.

## 8. Prioritized GitHub implementation backlog

Small, independently mergeable issues with clear acceptance criteria. Suggested order/dependencies noted.

| ID | Title | Priority | Depends on | Acceptance criteria (summary) | Security tests |
|---|---|---|---|---|---|
| B-001 | ADRs 001–012 finalized in blueprint | P0 | — | Spec section 18 contains finalized ADRs with context/decision/consequences/migration | N/A (doc) |
| B-002 | Alembic lineage & schema drift clean on fresh DB | P0 | — | Single head; `alembic upgrade head` + `alembic check` pass on clean DB; downgrade strategy documented | Migration safety |
| B-003 | Tenant model (Organization + membership context) | P0 | B-001 | Additive schema + server-derived tenant context; backfill plan; no client-trusted org | Cross-tenant authz tests |
| B-004 | Propagate `organization_id` to tenant-owned entities | P0 | B-003 | Engagements/runs/findings/evidence/reports/approvals scoped by org with FKs/indexes | Cross-tenant isolation |
| B-005 | Approval workflow model & API | P0 | B-003,B-004 | Request/decide/list approvals; audited; required states enforced | Authz + audit tests |
| B-006 | Policy decision service & enforcement hook | P0 | B-003,B-004 | Central `authorize(action, subject, context)` records allow/deny decisions | Deny-bypass tests |
| B-007 | Policy-gated, scope-validated run enqueue | P0 | B-005,B-006 | Runs require valid approval/policy allow; scope checked pre-enqueue; decision recorded | Scope/policy bypass tests |
| B-008 | Run/job traceability & state transitions | P1 | B-004,B-007 | Correlation IDs, state history/events, idempotency where applicable | Audit/trace tests |
| B-009 | Runner execution manifest & isolation hardening (baseline) | P0 | B-007 | API does not execute tools; worker/runner consumes scoped manifest; limits/profile applied | Isolation/containment tests |
| B-010 | Evidence integrity & provenance fields | P0 | B-004,B-008 | SHA-256, storage/provenance metadata, authorized access; linked to run/finding | Integrity/access tests |
| B-011 | Findings normalization linkage | P1 | B-008,B-010 | Findings linked to tenant/engagement/run/asset context; normalized fields | Consistency tests |
| B-012 | Traceable report generation | P0 | B-010,B-011 | Report records include org/engagement/run/evidence refs and integrity/provenance metadata | Traceability tests |
| B-013 | AI advisory-only enforcement & audit completeness | P0 | B-006 | AI endpoints cannot trigger execution; all calls audited with bounded data | Policy-bypass tests |
| B-014 | Auth/session/CSRF/CORS hardening per environment | P1 | B-003 | Secure cookie/CSRF posture, restricted CORS, token/key handling | Web/API security tests |
| B-015 | Versioned domain events & outbox (slice events) | P1 | B-008 | Emit required events with schema_version; idempotent consumers | Contract tests |
| B-016 | Observability baseline (logs/metrics/correlation) | P1 | B-008 | Structured logs, key metrics, propagated correlation IDs | Ops smoke tests |
| B-017 | Web UX for slice (engagement, approval, run, findings, evidence, report) | P1 | B-005,B-007,B-012 | Authenticated flows reflect states/permissions; light/dark QA | E2E/UI tests |
| B-018 | CI gates for slice security invariants | P1 | B-003–B-013 | Automated checks for tenancy, policy, scope, isolation, evidence, report traceability | Gate enforcement |
| B-019 | CLI contract alignment & tests for new commands | P2 | — | Commands match API contracts; mocked/live smoke tests | Contract tests |
| B-020 | Dependency & SAST pipeline reliability (Bandit/Safety/gitleaks) | P1 | — | Reproducible scans; findings triaged/remediated or accepted | Supply-chain checks |

## 9. Rollout and migration notes
- **Additive first:** nullable columns/backfills before constraints; feature flags or compatibility paths for existing clients.
- **Backfill:** assign legacy engagements to a default/bootstrap organization with explicit admin action/migration script.
- **Preservation rule:** no destructive refactors; keep existing routes/models working while introducing tenant/policy layers.
- **Verification before promotion:** run slice security tests, migration upgrade on clean DB, and smoke flows in staging.

## 10. Definition of done (first vertical slice)
- All B-003–B-013 and B-012 acceptance criteria met for the slice scope (with B-002, B-014, B-018 at least enforced for the slice paths).
- End-to-end demo: authenticated user (scoped to org) → create engagement + scope → approval → policy-approved run → isolated execution → normalized findings → evidence with checksum/provenance → traceable report.
- Automated tests pass for the five review-focus failure modes; CI gates prevent regressions on covered paths.
- Documentation updated: ADRs, API/event contracts, migration/runbook notes. 

---

*This document is a planning/specification artifact to be refined as ADRs are finalized and implementation proceeds. Create GitHub issues from B-001…B-020 with owners, estimates, and dependency links.* 
