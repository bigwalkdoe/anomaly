# Anomaly Full Platform — Implementation Specification and Prioritized Backlog

> **Task 3 deliverable** — Define implementation specification and prioritized backlog  
> **Date:** 2026-11-10  
> **Blueprint:** `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md` (v1.0, target-state)  
> **Gap analysis:** `docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md`  
> **Implementation plan:** `docs/superpowers/plans/2026-11-10-anomaly-full-platform-design-blueprint.md`  
> **Status:** Draft — repository-aware specification for the first delivery slice

## 1. Purpose and scope

This document converts the finalized blueprint and gap analysis into an actionable, repository-aware implementation specification for the **first production-grade vertical slice** (Blueprint §17) and a prioritized GitHub issue backlog. It is the Task 3 deliverable consumed by Task 4 (execution).

**First delivery slice (end-to-end):**

1. User authenticates — organization membership and permissions are loaded.
2. User creates engagement — scope and exclusions are recorded.
3. Engagement receives approval — authorization and approver are audited.
4. User requests assessment — policy validates authorization and scope.
5. Worker executes — an isolated runner performs the approved operation.
6. Results are normalized — findings are stored and associated with assets.
7. Evidence is preserved — checksums and provenance are recorded.
8. Report is generated — organization receives a traceable report.

**Constraints (binding):** preserve existing working functionality; prefer additive migrations and incremental refactoring; no destructive restructuring or staging deployment changes before backups are verified and the current environment is documented (plan global constraints). The live repository uses unversioned `/api/...` routes and `apps/api`, `apps/worker`, `apps/cli`, `apps/web`, `packages/{core,tools,ai,reporting,integrations,common}`; ADR-001 retains this modular-monolith layout and defers physical splits.

## 2. Inputs and governing decisions

| Input | Governs |
| --- | --- |
| ADR-001 (modular monolith) | Keep control plane in `apps/api` + `packages/*`; add services behind routers; no premature service split. |
| ADR-002 (multi-tenant isolation) | Add `organizations`, `workspaces`, `memberships`; mandatory org identifiers on tenant-owned records; explicit tenant context; RLS where appropriate; tenant-partitioned object paths; cross-tenant tests. |
| ADR-003 (identity & authorization) | RBAC permission subset + resource-level policy engine; consistent enforcement on APIs/workers/WebSockets/evidence/report exports; auditable deny events. |
| ADR-004 (runner isolation) | Separate runner trust boundary with authenticated execution manifest, short-lived scoped credentials; implement Standard tier first; wire approval gating before real execution. |
| ADR-005 (scope enforcement) | Central policy engine decides; resolve every destination (allowlists, exclusions, DNS, redirects, IPv4/IPv6, private/link-local, rebinding, expiry, mid-execution changes); audit decisions. |
| ADR-006 (events/jobs) | Versioned event contracts (`schema_version`), transactional outbox, idempotent consumers, Redis+ARQ initially. |
| ADR-007 (evidence integrity) | SHA-256 at ingest, provenance (org/engagement/job/asset/finding), retention policy, access control before retrieval/export. |
| ADR-008 (AI architecture) | Provider-independent gateway; policy-gated AI-proposed execution; usage metering; AI proposes, policy authorizes. |
| ADR-012 (API/event versioning) | Target `/api/v1/` with `success/data/meta` envelope, idempotency/correlation IDs; evolve compatibly (transitional handling for unversioned clients). |

**Gap-analysis drivers for the slice:** tenancy model missing; policy engine missing; approval not wired into execution; runner default is `FakeRunner`/hardened Docker path incomplete; evidence lacks enforced checksums/retention; reports lack end-to-end traceability; API contract alignment partial.

## 3. First-slice architecture and delivery boundaries

The slice is delivered **incrementally and additively** inside the existing monolith:

- **Control plane (API):** `apps/api/src/anomaly_api/` routers call application services; services enforce tenant context and policy decisions before state changes or job enqueue.
- **Domain & persistence:** `packages/core/src/anomaly_core/` models, scope/policy/runner/audit primitives, and Alembic migrations under `packages/core/alembic/versions/`.
- **Execution:** `apps/worker/src/` continues to consume ARQ jobs; worker validates manifest/policy/scope and invokes a runner implementing the execution-manifest contract (Standard isolation tier for the slice).
- **Evidence & reporting:** `packages/core`/`packages/reporting` persist checksummed evidence with provenance and generate engagement reports traceable to org/engagement/job/execution/findings/evidence.
- **Web (in-scope where needed):** `apps/web/` surfaces only the minimal UX required to exercise the slice flow (auth context, create engagement/scope, approval action, request assessment, view results/report) — expanded navigation remains later work.

**Out of scope for Task 4 implementation (backlogged):** full asset intelligence inventory/graph, incidents/defensive monitoring, full workflow engine, billing/entitlements, complete `/api/v1` migration of all legacy endpoints, RLS rollout beyond slice tables (where safe), Enhanced/High-assurance runners, staging/production hardening.

## 4. Exact files, migrations, interfaces, and tests (first delivery slice)

Paths are relative to repository root. “Create” means add a new file; “Modify” means change an existing file additively unless noted.

### 4.1 Tenancy, identity context, and RBAC/policy foundation (slice steps 1–4)

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `packages/core/alembic/versions/<rev>_add_tenancy_models.py` | Add `organizations`, `workspaces`, `memberships` tables; add nullable-then-backfilled `organization_id` (and `workspace_id` where applicable) FKs to `engagements` and other slice-touched tenant-owned records; indexes/constraints; default-org backfill for existing rows to preserve behavior. |
| Create | `packages/core/src/anomaly_core/models/tenancy.py` | SQLAlchemy models: `Organization`, `Workspace`, `Membership` (user_id, organization_id, workspace_id?, role/permissions linkage as appropriate), timestamps. |
| Modify | `packages/core/src/anomaly_core/models/__init__.py` | Export tenancy models. |
| Modify | `packages/core/src/anomaly_core/models/engagement.py` | Add `organization_id`, `workspace_id` columns/relationships; extend engagement lifecycle/status to include approval states needed by slice (`draft`, `pending_approval`, `approved`, `active`/`completed` as applicable) with safe defaults for existing data. |
| Modify | `packages/core/src/anomaly_core/models/finding.py` | Ensure `Evidence` (and `Report` where applicable) carry `organization_id`/provenance fields required for traceability (additive). |
| Modify | `packages/core/src/anomaly_core/models/run.py` | Add approval/manifest/provenance fields needed to bind execution to approval, scope, org, engagement (additive). |
| Modify | `packages/core/src/anomaly_core/models/audit.py` | Ensure audit records can carry `organization_id`, actor, action, resource, decision context (additive). |
| Create | `packages/core/src/anomaly_core/tenancy.py` | Tenant context resolution helpers (derive org/workspace/membership from authenticated user; no trust of client-supplied org id without membership check). |
| Create | `packages/core/src/anomaly_core/policy.py` | Resource-level `PolicyEngine`/`PolicyDecision` evaluating membership, resource ownership, engagement scope/approval state, requested permission; emits auditable deny reasons. |
| Modify | `packages/core/src/anomaly_core/rbac.py` | Expand permission checks to integrate policy decisions for slice operations (additive). |
| Modify | `packages/core/src/anomaly_core/auth.py` | Token/session claims or loading path to expose membership/permissions context required by step 1 (additive). |
| Modify | `packages/core/src/anomaly_core/scope.py` | Extend `check_scope` toward ADR-005 for the slice: validate resolved destinations for run targets (allowlist/exclusion match, private/link-local handling as configured) and record decision/warnings; full redirect/rebinding hardening tracked in backlog but interface defined here. |
| Create | `apps/api/src/anomaly_api/services/policy_service.py` | Application service: authorize engagement create/approve/assessment request, evidence/report access; centralize tenant + policy checks. |
| Create | `apps/api/src/anomaly_api/services/engagement_service.py` | Create engagement + scope/exclusions, submit/approve transitions, audit emission. |
| Modify | `apps/api/src/anomaly_api/deps.py` | Dependencies to load current user, tenant context, and enforce membership on engagement/resource access. |
| Modify | `apps/api/src/anomaly_api/routers/auth.py` | Login/me responses include organization memberships and effective permissions/roles for the slice (additive fields). |
| Modify | `apps/api/src/anomaly_api/routers/engagements.py` | Scope/approval-aware create/update/approve endpoints (or additive actions) enforcing policy and auditing. |
| Create | `apps/api/src/anomaly_api/schemas/tenancy.py` | Pydantic schemas for organization/workspace/membership context in responses (additive). |
| Modify | `apps/api/src/anomaly_api/schemas/engagement.py` | Add scope/exclusion, approval, org/workspace fields as needed. |

**Tests (slice-critical):**
- Create/modify `tests/core/test_tenancy.py` — tenant context resolution and membership enforcement.
- Create/modify `tests/api/test_tenancy_isolation.py` — cross-tenant access to engagements/evidence/reports returns 403/404 per existing conventions (must not leak existence).
- Modify `tests/api/test_engagements.py`, `tests/api/test_auth.py`, `tests/core/test_rbac_seed.py` — cover memberships/permissions in auth, engagement lifecycle with approval, policy-denied paths audited.

### 4.2 Assessment request, approval gating, and execution (slice steps 3–5)

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `packages/core/alembic/versions/<rev>_execution_manifest_and_approvals.py` | Add/adjust run/approval fields for manifest binding (job/run id, org, engagement, approved scope ref, tool id/version, limits, expiration, policy decision ref), execution state transitions, and linkage of approval to assessment request. |
| Create | `packages/core/src/anomaly_core/execution.py` | `ExecutionManifest` dataclass/model helpers: construction, validation, expiry, and serialization for worker. |
| Modify | `packages/core/src/anomaly_core/runner.py` | Define/extend runner interface to accept an authenticated `ExecutionManifest`; keep `FakeRunner` for tests; add/complete Standard isolated Docker runner path with manifest-driven, least-privilege invocation (no API-process execution). |
| Modify | `apps/api/src/anomaly_api/routers/runs.py` | “Request assessment” path: require approved engagement/scope, evaluate policy (authz + scope + approval), create run/job manifest, enqueue only when authorized; emit audit and (when outbox present) assessment events. |
| Create | `apps/api/src/anomaly_api/services/run_service.py` | Orchestrate validation → authorization → approval check → manifest creation → queue enqueue; idempotency key support for request where feasible. |
| Modify | `apps/worker/src/anomaly_worker/tasks.py` (or equivalent task module) | Consume run job, re-validate manifest/policy/scope before execution, invoke runner, capture outputs/artifacts, record state transitions and failures. |
| Modify | `packages/tools/src/anomaly_tools/registry.py` and relevant adapters (`nmap.py`, `httpx.py`, etc., as used by slice) | Ensure adapters accept structured input and return normalized outputs/errors; adapters must not make authorization decisions (policy enforced by service/worker). |

**Tests (slice-critical):**
- Modify `tests/core/test_runner.py` — manifest contract, Standard-runner invocation boundaries (unit/mocked), no in-process tool execution.
- Create `tests/api/test_runs_policy.py` — unapproved or out-of-scope requests denied and audited; approved in-scope requests enqueue.
- Modify `tests/api/test_runs.py`, `tests/api/test_runs_e2e.py` — end-to-end approved execution path with `FakeRunner`/controlled runner producing normalized results.
- Create `tests/security/test_scope_enforcement.py` — resolved-destination checks for representative cases (allow/deny, private/link-local) per slice scope.

### 4.3 Findings normalization, evidence integrity, and reporting (slice steps 6–8)

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `packages/core/alembic/versions/<rev>_evidence_integrity_traceability.py` | Add `sha256`, provenance fields (collector identity, tool/version, job/run/execution refs, storage location/key), classification/retention metadata to evidence; report traceability fields/checksum linkage as needed. |
| Create | `packages/core/src/anomaly_core/evidence.py` | Evidence ingest service/helpers: compute SHA-256, bind provenance, persist metadata, store artifact via MinIO/object-storage abstraction with tenant-partitioned keying. |
| Modify | `packages/core/src/anomaly_core/models/finding.py` | Evidence/Report fields for integrity and traceability. |
| Modify | `packages/reporting/src/` (generator module(s), e.g. `generator.py`/package entry) | Generate report for an engagement that includes traceable references to organization, engagement, job/run, execution, findings, and evidence checksums/provenance. |
| Modify | `apps/api/src/anomaly_api/routers/evidence.py` | Ingest/retrieve with authorization-before-retrieval and integrity metadata exposure. |
| Modify | `apps/api/src/anomaly_api/routers/reports.py` | Generate/download report with policy enforcement and audit logging. |
| Modify | `apps/api/src/anomaly_api/routers/findings.py` | Persist normalized findings associated to engagement/assets/targets as applicable to slice inputs. |

**Tests (slice-critical):**
- Create `tests/core/test_evidence_integrity.py` — SHA-256 computed and verified; tamper/mismatch detected.
- Create `tests/reporting/test_report_traceability.py` — generated report contains org/engagement/job/execution/finding/evidence traceability.
- Modify `tests/api/test_evidence.py`, `tests/api/test_findings.py` — authorization, provenance persistence, end-to-end linkage.

### 4.4 Events and audit (cross-cutting)

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `packages/core/alembic/versions/<rev>_event_outbox.py` | Transactional outbox table (`event_id`, `event_type`, `schema_version`, org/engagement/job ids, `occurred_at`, payload, publish state/idempotency metadata). |
| Create | `packages/core/src/anomaly_core/events.py` | Event envelope builder/validation and outbox write helpers; idempotent publish interface (publisher can be minimal/no-op consumer-side in slice, but contract enforced). |
| Create | `contracts/events/*.schema.json` (or `docs/contracts/events/` if `contracts/` dir is not introduced yet) | Versioned JSON Schemas for slice events: at minimum `engagement.approved`, `assessment.requested`, `assessment.started`, `assessment.completed`/`assessment.failed`, `evidence.collected`, `finding.created`, `policy.denied` (per envelope in §5.2). |
| Modify | `packages/core/src/anomaly_core/audit.py` and API/worker call sites | Emit auditable events for approvals, policy decisions (including denies), assessment lifecycle, evidence/report access.

**Tests:**
- Create `tests/core/test_events.py` — envelope fields and `schema_version` present; outbox write occurs transactionally with state changes for slice actions.

### 4.5 Web (minimal slice UX)

| Action | File | Responsibility |
| --- | --- | --- |
| Modify | `apps/web/app/**` (engagements, runs/assessments, findings, reports/evidence views as present) | Minimal flows to authenticate with membership context, create engagement + scope, approve, request assessment, and view findings/evidence/report status. Follow existing Next.js/TS patterns; server/API remains authority. |
| Modify | `apps/web/lib/**` or API client modules (as applicable) | Support additive auth/context and slice endpoint calls. |

**Tests:** extend existing web tests/build checks as applicable in CI (`npm test`/`npm run build` in `apps/web`).

## 5. API contracts and event schemas (first slice)

### 5.1 API conventions (additive, slice-scoped)

- **Transitional versioning (ADR-012):** introduce slice endpoints under `/api/v1/...` where practical; existing `/api/...` endpoints remain functional. New slice responses SHOULD use the envelope `{"success": true|false, "data": ..., "meta": {"request_id": "<uuid>", ...}}`; error responses include structured codes/messages without secrets or internal traces.
- **AuthN/AuthZ:** all slice endpoints require authenticated user; tenant context derived server-side from membership; authorization and scope/policy decisions enforced in services (403 on denied, 404 where existence must not leak, per existing app behavior).
- **Idempotency:** assessment request accepts optional `Idempotency-Key` header (or request field) to prevent duplicate enqueue on retry (best-effort in slice; full guarantee via outbox/consumer idempotency).

### 5.2 Slice endpoint specifications

| Method | Path (v1 target) | Purpose | Request (key fields) | Success `data` (key fields) | AuthZ/notes |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | Authenticate | `email`, `password`, MFA fields as required | `access_token`, `refresh_token`/session, `user`, `memberships[]` (org/workspace ids, roles/permissions) | Existing login semantics preserved; additive membership payload. |
| GET | `/api/v1/auth/me` | Current identity & context | — | `user`, `memberships[]`, effective permissions | Server-derived context. |
| POST | `/api/v1/engagements` | Create engagement (step 2) | `organization_id`/workspace (validated against membership), `name`, `scope`/`exclusions`, dates/limits as supported | engagement object incl. `id`, `organization_id`, `status` (`draft`/`pending_approval` as applicable), scope | Policy + membership required; audited. |
| POST | `/api/v1/engagements/{id}/submit` (or equivalent action) | Submit for approval | — / comment | engagement with `status=pending_approval` | Owner/authorized role; audited. |
| POST | `/api/v1/engagements/{id}/approve` | Approve engagement (step 3) | optional `comment` | engagement with `status=approved`, `approved_by`, `approved_at` | Approver permission + policy; audited (approver identity). |
| POST | `/api/v1/engagements/{id}/assessments` (or `/runs` request) | Request assessment (step 4) | `tool`, `targets`/scope ref, `params`, `limits`, `idempotency_key?` | run/job `{id, status, engagement_id, organization_id, manifest_ref}` | Requires approved engagement & in-scope targets; policy validates authz+scope; denied decisions audited; enqueues only when authorized. |
| GET | `/api/v1/runs/{id}` | Run status/results | — | run with `status`, transitions, `scope_warning`/policy refs, normalized result refs | Tenant/policy-checked. |
| GET | `/api/v1/engagements/{id}/findings` | Findings (step 6) | — | `items[]` findings with normalized fields, associations | Tenant/policy-checked. |
| POST | `/api/v1/evidence` (or run-scoped ingest) | Preserve evidence (step 7) | artifact + metadata (`run_id`/`job_id`, `finding_id?`, type) | evidence `{id, sha256, organization_id, engagement_id, job_id, run_id, storage_key, provenance}` | Checksum computed at ingest; authorization before storage/read. |
| GET | `/api/v1/evidence/{id}` | Retrieve evidence metadata/artifact | — | metadata (+ authorized download) | Authorization before retrieval/export. |
| POST | `/api/v1/engagements/{id}/reports` | Generate report (step 8) | `format` (supported subset) | report `{id, format, status/location, checksum?, traceability}` | Tenant/policy-checked; audited. |
| GET | `/api/v1/engagements/{id}/reports/{report_id}` | Download report | — | artifact | Authorization before download; traceable to org/engagement/job/execution/findings/evidence. |

*Legacy compatibility:* existing `/api/...` routes used by current clients/tests continue to work; where v1 duplicates behavior, handlers may delegate to shared services to avoid drift.

### 5.3 Event schemas (versioned contracts)

All events share the envelope (ADR-006 / Blueprint §5.3):

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "schema_version": 1,
  "organization_id": "uuid",
  "engagement_id": "uuid|null",
  "job_id": "uuid|null",
  "occurred_at": "RFC3339 timestamp",
  "payload": {}
}
```

| `event_type` | When emitted | `payload` (minimum fields) | Idempotency key |
| --- | --- | --- | --- |
| `engagement.approved` | Step 3 approval committed | `approver_id`, `previous_status`, `new_status`, `comment?` | `event_id` / outbox row id |
| `policy.denied` | Any slice policy denial | `actor_id`, `action`, `resource_type`, `resource_id?`, `reason_code`, `reason` (non-sensitive) | `event_id` |
| `assessment.requested` | Authorized request accepted/enqueued | `run_id`, `tool`, `scope_ref`, `requested_by` | `run_id` + `event_type` |
| `assessment.started` | Worker begins execution | `run_id`, `runner`, `manifest_ref` | `run_id` + `event_type` |
| `assessment.completed` | Execution succeeded with normalized results | `run_id`, `result_summary`, `findings_count`, `evidence_ids[]` | `run_id` + `event_type` |
| `assessment.failed` | Execution failed/terminated | `run_id`, `error_class`, `retryable` | `run_id` + `event_type` |
| `finding.created` | Normalized finding persisted | `finding_id`, `run_id`, `severity`, `asset_ref?` | `finding_id` + `event_type` |
| `evidence.collected` | Evidence ingested & checksummed | `evidence_id`, `run_id`, `sha256`, `storage_key`, `finding_id?` | `evidence_id` + `event_type` |

Schemas evolve compatibly; consumers must be idempotent on (`event_type`, natural key/id).

## 6. Execution manifest (slice contract)

Minimum manifest fields passed from control plane to worker/runner (ADR-004):

| Field | Description |
| --- | --- |
| `job_id` / `run_id` | Unique execution identifier. |
| `organization_id`, `engagement_id` | Tenant and engagement binding. |
| `approved_scope_ref` | Reference to approved scope/exclusions snapshot used for validation. |
| `tool_id`, `tool_version` | Tool adapter identity/version. |
| `targets`, `params` | Structured, policy-validated inputs. |
| `resource_limits` | Timeout, CPU/memory/output limits. |
| `expires_at` | Manifest/approval validity bound. |
| `output_destination` | Scoped location for results/artifacts (tenant-partitioned). |
| `execution_policy` | Policy decision/constraints (no unrestricted credentials). |
| `credentials_ref` | Short-lived scoped credential handle (if required); never embedded secrets. |

Worker re-validates manifest freshness, approval, and scope before invoking the runner.

## 7. Prioritized GitHub issue backlog

Issues are **small, independently mergeable** where possible, carry explicit acceptance criteria, and reference ADRs/gaps. Create in this order; dependencies noted. (Labels/components are suggestions.)

### P0 — First vertical slice (Task 4 scope)

| ID | Title | Depends on | Acceptance criteria |
| --- | --- | --- | --- |
| BL-001 | Tenancy foundation: organizations, workspaces, memberships | — | Additive migration creates `organizations/workspaces/memberships` and backfills default org for existing engagements/users; models exported; tenant context resolved server-side from membership; no regression to existing auth/engagement flows; tests cover membership resolution and deny on non-member. (ADR-002) |
| BL-002 | Engagement lifecycle with scope, exclusions, and approval states | BL-001 | Engagement create persists scope/exclusions bound to org/workspace; states support submit/approve with `approved_by/approved_at`; only authorized approver can approve; all transitions audited; API/service tests pass. (ADR-003, §3.7) |
| BL-003 | Resource-level policy engine (slice) and auditable deny decisions | BL-001 | `PolicyEngine` evaluates membership, ownership, engagement state/scope, and requested permission for slice actions; denies emit `policy.denied` audit/event with reason; APIs/workers use central decisions (no adapter authz). (ADR-003, ADR-005) |
| BL-004 | Assessment request with policy + scope + approval gating | BL-002, BL-003 | Request endpoint enqueues run only when engagement approved and targets in scope; out-of-scope/unapproved/unauthorized requests rejected and audited; idempotency handled best-effort; run bound to org/engagement/manifest ref. (ADR-004, ADR-005) |
| BL-005 | Execution manifest and Standard isolated runner path | BL-004 | Manifest carries required fields (org/engagement/scope ref/tool/version/limits/expiry/output policy); worker re-validates before execution; Standard runner executes outside API process with least privilege; `FakeRunner` remains for tests. (ADR-004) |
| BL-006 | Normalized findings linkage for slice assessments | BL-004 | Tool outputs normalized into findings persisted with engagement/run associations and severity/status; normalization errors surfaced without corrupting state. |
| BL-007 | Evidence integrity, provenance, and tenant-partitioned storage | BL-001, BL-006 | SHA-256 computed at ingest and stored; evidence records org/engagement/job/run/finding refs, collector/tool metadata, storage key; authorization before retrieval/export; integrity verification test passes. (ADR-007) |
| BL-008 | Traceable engagement report generation | BL-006, BL-007 | Report generation produces artifact referencing organization, engagement, job/run, execution, findings, and evidence checksums/provenance; access controlled and audited. (Review Focus #5) |
| BL-009 | Versioned events/outbox for slice lifecycle | BL-002–BL-008 | Outbox + envelope with `schema_version` for slice events; emits `engagement.approved`, `policy.denied`, `assessment.*`, `finding.created`, `evidence.collected` transactionally with state changes; idempotent consumer contract documented. (ADR-006) |
| BL-010 | Cross-tenant, scope-bypass, and AI/policy regression tests for slice | BL-001–BL-009 | Automated tests cover cross-tenant isolation on slice resources, resolved-destination scope denial cases, policy-gated execution (no bypass), evidence checksum integrity, and report traceability; CI green. (Review Focus #1–#5) |

### P1 — Contract, platform hardening, and completeness

| ID | Title | Depends on | Acceptance criteria |
| --- | --- | --- | --- |
| BL-011 | `/api/v1` envelope and transitional routing for slice APIs | BL-001–BL-008 | v1 routes return `success/data/meta` with `request_id`; legacy routes preserved; OpenAPI documents v1 slice. (ADR-012) |
| BL-012 | Runner hardening and scope-resolution depth | BL-005 | Extend scope validation for redirects/DNS rebinding/IPv6/private ranges per config; harden container profile (no-new-privileges, caps drop, resource limits) for Standard tier with tests. (ADR-004, ADR-005) |
| BL-013 | Evidence retention enforcement and access audit | BL-007 | Retention metadata enforced via scheduled disposition; all evidence/report access audited. (ADR-007) |
| BL-014 | Minimal web flows for vertical slice | BL-002, BL-004, BL-008 | UI supports auth context, create/scope/approve engagement, request assessment, view findings/evidence/report for authorized users. |
| BL-015 | RLS pilot and repository/service scoping for tenant tables | BL-001 | Apply PostgreSQL RLS policies for slice tenant-owned tables where appropriate; automated cross-tenant DB-level tests. (ADR-002) |

### P2 — Broader blueprint backlog (deferred)

| ID | Title | Acceptance criteria |
| --- | --- | --- |
| BL-016 | Asset intelligence domain (inventory, relationships, lifecycle) | Models/APIs/UI for assets/observations/relationships with authorized lifecycle states. |
| BL-017 | Defensive monitoring and incident management | Security events/alerts/incidents with investigation timelines and response playbooks. |
| BL-018 | AI sessions, usage metering, and policy-gated actions | Session/usage records, provider gateway hardening, explicit policy gate on any AI-proposed execution. (ADR-008) |
| BL-019 | Workflow engine and approvals generalization | Workflow definitions/runs/steps integrated with policy and audit. |
| BL-020 | Billing, subscriptions, and entitlement evaluation | Plans/subscriptions/usage records with entitlement checks separate from core authz. (ADR-011) |
| BL-021 | Full API v1 migration, OpenAPI envelope parity, and event schema registry | All public endpoints versioned with consistent envelope; published schema registry and compatibility policy. (ADR-012) |
| BL-022 | Observability, backup/recovery, and production deployment hardening | Metrics/alerts, RPO/RTO automation, staging, hardened Helm/compose, secrets/TLS, runner nodes. (ADR-009, ADR-010) |
| BL-023 | Tool coverage expansion (OWASP ZAP, Nikto) and adapter conformance | Adapters added with versioning, normalization, limits, scope/policy conformance. |

## 8. Test strategy for the slice (Task 4 gate)

| Area | Required coverage | Location (target) |
| --- | --- | --- |
| Authentication & context | Memberships/permissions loaded on auth | `tests/api/test_auth.py`, `tests/core/test_tenancy.py` |
| Tenancy isolation (Review Focus #1) | Cross-tenant read/write denied, no existence leak | `tests/api/test_tenancy_isolation.py` |
| Engagement approval | Create/scope/approve lifecycle and audit trail | `tests/api/test_engagements.py` |
| Policy & scope (Review Focus #2) | Deny unapproved/out-of-scope; auditable denies; resolved-destination cases | `tests/api/test_runs_policy.py`, `tests/security/test_scope_enforcement.py` |
| Runner isolation boundary (Review Focus #2) | Manifest-driven execution outside API; Standard-runner contract (mocked/integration) | `tests/core/test_runner.py`, `tests/api/test_runs_e2e.py` |
| AI policy (Review Focus #3) | No AI-proposed execution bypasses policy/approval gates (slice: suggestions advisory; execution gated) | `tests/ai/test_ai.py`, `tests/api/test_runs_policy.py` |
| Evidence integrity (Review Focus #4) | SHA-256 computed/verified; provenance persisted | `tests/core/test_evidence_integrity.py`, `tests/api/test_evidence.py` |
| Report traceability (Review Focus #5) | Report references org/engagement/job/execution/findings/evidence | `tests/reporting/test_report_traceability.py` |
| End-to-end slice | Authenticate → create/scope → approve → request → execute → findings → evidence → report | `tests/api/test_vertical_slice_e2e.py` |

Verification command for Task 4: `pytest -v` (with environment/services required by existing suites); web checks as configured.

## 9. Risks, assumptions, and open decisions

- **Migration safety:** tenancy columns must be introduced additively with backfill/defaults so existing single-tenant data and tests continue to pass.
- **RLS timing:** full RLS enablement can be staged (BL-015) after application-level enforcement proves correct, per ADR-002 “where appropriate”.
- **Runner realism:** the slice must prove the execution boundary and manifest contract; production-grade container hardening and node isolation deepen in BL-005/BL-012.
- **API compatibility:** dual `/api` and `/api/v1` behavior during transition must not break existing CLI/web clients.
- **Asset linkage:** full asset domain (BL-016) is deferred; slice may associate findings/evidence to targets/engagement context with an additive path to assets.

## 10. Definition of done (this specification)

- Exact files to create/modify for the first delivery slice are enumerated (§4).
- Required migrations and data changes are specified (§4, per-area).
- Interfaces (policy, tenancy context, execution manifest, evidence/report services) are defined (§4, §6).
- Slice API contracts and versioned event schemas are defined (§5).
- Prioritized, dependency-ordered GitHub issue backlog with acceptance criteria is provided (§7).
- Test strategy covering the five review-focus failure modes is specified (§8).

This document is ready to drive Task 4 implementation once reviewed and accepted.