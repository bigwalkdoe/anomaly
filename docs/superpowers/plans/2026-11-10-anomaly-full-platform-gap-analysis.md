# Anomaly Full Platform Gap Analysis

> **Task 1 deliverable** - Baseline repository inventory and gap analysis
> **Date:** 2026-11-10
> **Blueprint:** `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`
> **Implementation plan:** `docs/superpowers/plans/2026-11-10-anomaly-full-platform-design-blueprint.md`
> **Status:** Draft - target-state versus live repository

## 1. Purpose and scope

This document is the Task 1 deliverable of the Anomaly Full Platform Design
Blueprint implementation plan. It reconciles the target-state blueprint against
the live repository and produces the baseline inventory and gap analysis that
later tasks (ADR finalization, implementation specification, vertical slice)
consume.

The blueprint describes the target-state architecture ("Security Operations &
Intelligence Platform - Discover. Investigate. Validate. Respond. Govern.") and
explicitly does not claim the repository implements those capabilities. This
document closes that loop in the opposite direction: for every blueprint
component, it records the current implementation status and an accountable owner
for follow-up work.

## 2. Status vocabulary

| Status | Meaning |
| --- | --- |
| **Implemented** | Core capability present in source and exercised by tests; no known functional gap at the recorded level. |
| **Partial** | Building block exists, but key behaviors, lifecycle stages, or contract details are missing or stubbed. |
| **Missing** | No implementation found in the live repository. |
| **Deprecated** | Implemented but superseded by a newer design or approach. |
| **Unverified** | Present in source or documentation but not validated by tests, runs or review. |

Every status below is derived from source-level inspection of the live
repository (code, models, migrations, tests, infrastructure-as-code, CI) and is
citing evidence where applicable. Blueprint prose itself is treated as design
input, not as verification evidence.

## 3. Method

1. Inventory all applications, packages, endpoints, tables, integrations and
   deployments relevant to the blueprint domains.
2. Compare against the blueprint's target-state components, data model, API
   surface, execution engine, security and operations requirements.
3. Assign a status per blueprint component and an accountable owner for the
   next action.
4. Record cross-cutting risks, especially the five blueprint review-focus
   failure modes.

## 4. Baseline repository inventory

### 4.1 Applications checklist

- [ ] `apps/api` - FastAPI control-plane application. Status: **Partial**.
      Present: auth, MFA, lockout, RBAC, engagements, scope, findings, runs,
      audit, users, dashboard, stats, tags, webhooks, notifications, playbooks,
      upload, search, evidence, api keys, metrics, schedules, reports,
      vulnerabilities summary, AI suggest-tools, health, WebSocket.
      Missing: organizations, workspaces, assets, incidents, policies,
      approvals, workflows routers.
- [ ] `apps/worker` - ARQ background worker executing tool runs. Status:
      **Partial**. Executes `execute_run_task`; executor resolves tool via
      registry and calls runner. Default runner is `FakeRunner`; real execution
      path is stubbed.
- [ ] `apps/cli` - CLI surface (`ai`, `dashboard` commands). Status:
      **Partial**.
- [ ] `apps/web` - Next.js web application. Status: **Partial**. Pages exist
      for dashboard, engagements, findings, runs, reports, playbooks, schedules,
      settings and auth; navigation covers a small subset of blueprint areas.

### 4.2 Packages checklist

- [ ] `packages/core` - Foundation package (db, config, auth, RBAC, MFA, scope,
      runner, audit, logging, models, types). Status: **Implemented** for the
      foundation blocks present; model surface limited to engagements/findings/
      runs/evidence/reports/tags rather than full blueprint domain model.
- [ ] `packages/tools` - Tool registry and adapters (nmap, httpx, recon,
      nuclei, ffuf, sqlmap, stub). Status: **Partial** - OWASP ZAP and Nikto
      required by the blueprint are absent.
- [ ] `packages/ai` - AI provider adapters (ollama/openai/anthropic) and
      `AIService` with audit logging. Status: **Partial** - no AI sessions,
      usage metering, or policy-gated AI actions yet.
- [ ] `packages/reporting` - `ReportGenerator` (markdown/html/pdf). Status:
      **Partial** - PDF is a byte-stub; JSON/CSV and compliance mappings absent.
- [ ] `packages/integrations` - Spectre agent/suite clients. Status:
      **Partial**.
- [ ] `packages/common` - Shared schemas/utils. Status: **Partial**.

### 4.3 Data model and migrations checklist

- [ ] `users`, `roles`, `permissions`, `user_role`, `api_keys`, `refresh_tokens`,
      `login_attempts`, `mfa_secrets` - Present. Status: **Implemented**.
- [ ] `engagements`, `scopes`, `scope_entries`, `targets` - Present. Status:
      **Implemented** for engagement scoping baseline.
- [ ] `findings`, `evidence`, `reports`, `tags` - Present. Status:
      **Partial** (no SHA-256 checksum enforcement; no CVE mapping; no
      remediation/risk-acceptance lifecycle depth).
- [ ] `runs`, `playbooks`, `playbook_steps`, `cron_schedules`, `approvals`,
      `audit_logs` - Present. Status: **Partial**.
- [ ] Missing blueprint domains entirely: `organizations`, `workspaces`,
      `memberships`, `assets`, `asset_relationships`, `asset_observations`,
      `vulnerabilities`, `cve_records`, `incidents`, `alerts`, `security_events`,
      `workflows`, `workflow_runs`, `workflow_steps`, `ai_sessions`,
      `model_usage`, `ai_actions`, `policies`, `policy_decisions`, `billing`,
      `audit_checkpoints`.

### 4.4 API endpoint checklist

- [ ] Present blueprint-relevant endpoints: health/version, auth (register,
      login, refresh, logout, me, verify), MFA, lockout, RBAC, engagements,
      engagement scope, findings, runs, audit, users, dashboard, stats, tags,
      webhooks, WebSocket (runs/notifications), playbooks, upload, search,
      notifications, vulnerabilities summary, AI suggest-tools, API keys,
      metrics, schedules, reports, evidence, notifications.
- [ ] Missing: `/organizations`, `/workspaces`, `/assets`, `/assessments`,
      `/incidents`, `/policies`, `/approvals`, `/workflows`, `/billing`,
      compliance/audit export endpoints, AI knowledge/sessions endpoints.
- [ ] Contract alignment: blueprint specifies `/api/v1/` base path and
      `success`/`data`/`meta` response envelope; live API uses unversioned
      `/api/...` paths with ad-hoc response shapes. Status: **Partial**.

### 4.5 Tool integration checklist

- [ ] Nmap, Nuclei, HTTPX, FFUF, SQLMap adapters present.
- [ ] OWASP ZAP adapter: **Missing**.
- [ ] Nikto adapter: **Missing**.
- [ ] Generic/recon and stub adapters present.
- [ ] Tool version identification, structured input, timeout/resource limits,
  output normalization, error classification, scope enforcement, audit
  logging: partially covered by adapter/registry design.

### 4.6 Deployment and operations checklist

- [ ] Docker Compose (dev + prod) with Postgres, Redis, MinIO, API, web, worker,
      runner: **Partial/Implemented**.
- [ ] Helm chart (`deploy/helm/anomaly`): basic deployment/service/secret -
      **Partial**.
- [ ] CI (`.github/workflows/ci.yml`): lint, typecheck, tests, runner image
      build, bandit, safety, web build, gitleaks - **Partial**.
- [ ] Missing: staging environment, production monitoring stack (Prometheus +
      Grafana), backup/restore automation and recovery exercises, TLS/reverse
      proxy configuration in compose/helm, external secrets manager, Kubernetes
      runner deployment and isolation controls.

### 4.7 Tests and quality gates checklist

- [ ] Auth/MFA/lockout/RBAC/scope/runner/tools/AI/reporting/API/security tests
      present under `tests/` and package test trees - **Partial coverage** of
      blueprint release criteria.
- [ ] Missing: cross-tenant isolation tests, runner containment/escape tests,
      evidence integrity tests, approval/audit regression tests, load tests,
      deployment/recovery tests.

## 5. Gap analysis - blueprint components versus live status

### 5.1 Product and target-state architecture (Blueprint Section 2)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Modular monolith control plane with isolated execution services | Partial | FastAPI modular app present; isolated runner only stubbed (`packages/core/src/anomaly_core/runner.py`) | Backend owner |
| Core control-plane component set (identity/tenancy, engagements, assets, vulns, policy, workflow, AI, evidence, reporting) | Partial | Individual building blocks exist; no unified control-plane composition yet | Backend owner |

### 5.2 Application modules (Blueprint Section 3)

| Blueprint component | Status | Gap | Owner |
| --- | --- | --- | --- |
| Workspace dashboard | Partial | Overview aggregates engagements/findings; missing posture, system health, real-time updates | Frontend/Backend owner |
| Asset intelligence | Missing | No asset table or inventory/relationship model; engagement `targets` only | Backend owner |
| Vulnerability management | Partial | Findings with severity/status exist; missing CVE mapping, CVSS exploit context, dedup, risk acceptance, trends | Backend owner |
| Offensive security operations | Partial | Tool registry + run execution + scope checks; missing ZAP/Nikto, full lifecycle, approval gating | Security owner |
| Defensive monitoring / incidents | Missing | No incidents, alerts or security events implementation | Security owner |
| AI intelligence | Partial | Provider adapters, suggest-tools, audit; missing sessions, metering, policy-gated actions | AI owner |
| Engagement management | Partial | Engagements/scopes/targets exist; lifecycle missing `PENDING_APPROVAL`/`APPROVED`/`COMPLETED`/`ARCHIVED` states | Backend owner |
| Evidence management | Partial | Evidence rows exist; missing SHA-256 checksum, retention enforcement, access control depth | Security owner |
| Reporting and compliance | Partial | Markdown/HTML/PDF generation; PDF stub; missing JSON/CSV, versioned compliance mappings | Backend owner |

### 5.3 Identity, tenancy and authorization (Blueprint Section 4)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Platform - Organization - Workspace - Engagement hierarchy | Missing | No organization/workspace models or tenancy context anywhere in Python source | Security owner |
| Recommended roles and permissions | Partial | Seeded `admin`, `pentester`, `client_viewer` only; small permission set; blueprint lists eight roles plus granular permissions | Security owner |
| Authentication design (OIDC, MFA, sessions, API keys) | Partial | JWT + refresh rotation, TOTP MFA, backup codes, lockout, rate limits present; SAML and cookie/CSRF posture incomplete | Security owner |
| Authorization enforcement | Partial | RBAC + engagement-scoped access checks present; no resource-level policy engine | Security owner |

### 5.4 Data architecture (Blueprint Section 5)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| PostgreSQL system of record / Redis / MinIO | Partial | Compose and models align; Postgres/Redis/MinIO present; RLS not applied | Data owner |
| Core entity/tables | Partial | 20+ tables present; blueprint domains (assets, vulnerabilities, incidents, workflows, AI, policy, billing, audit checkpoints) absent | Data owner |
| Core relationships | Partial | Engagement->targets/findings, run->evidence, finding->evidence present; asset relationship model absent | Data owner |
| Data isolation | Missing | No organization identifiers or tenant context on tenant-owned records; no cross-tenant tests | Security owner |

### 5.5 Backend architecture (Blueprint Section 6)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| FastAPI + SQLAlchemy 2 + Alembic + Postgres/Redis ARQ/MinIO stack | Implemented | Stack and migrations present | Backend owner |
| Suggested package boundaries | Partial | Live packages (`core`, `tools`, `ai`, `reporting`, `integrations`, `common`) differ from blueprint list (`identity`, `tenancy`, `engagements`, `assets`, ...); runner/scheduler not separate apps | Backend owner |
| Layering rules | Partial | Service helpers exist; router-to-service boundary not consistently formalized | Backend owner |

### 5.6 Execution engine and isolation (Blueprint Section 7)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Orchestration chain (policy -> approval -> queue -> worker -> runner) | Partial | Worker + scope check + runner interface exist; approval flow not wired into execution path; queue is ARQ | Security owner |
| Execution manifest | Partial | `RunSpec`/`Run` carry tool, targets, params, limits, command; credential scoping/expiry not enforced | Security owner |
| Isolation levels | Missing | Only FakeRunner and stubbed DockerRunner; no Standard/Enhanced/High assurance tiers | Security owner |
| Container hardening baseline | Missing | DockerRunner `_build_args` sets `privileged: false`, `read_only: true`, mem/cpu limits; not executed as hardened runtime | Security owner |
| Scope enforcement | Implemented | `check_scope` resolves in/out scope with warnings; run flagged `scope_warning` | Security owner |
| Job lifecycle | Partial | `queued -> running -> succeeded/failed/cancelled`; missing `validating`, `awaiting_approval`, `collecting_results` | Backend owner |

### 5.7 Frontend and UX (Blueprint Section 8)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Main navigation and core pages | Partial | Nav covers Dashboard, Engagements, Findings, Runs, Reports; missing Assets, Vulnerabilities/Risk, Incidents, AI Assistant, Evidence, Governance, Administration | Frontend owner |

### 5.8 API architecture (Blueprint Section 9)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Versioned REST contract (`/api/v1/`, `success/data/meta` envelope) | Partial | Live paths under `/api/...` with ad-hoc shapes | Backend owner |
| Resource endpoints | Partial | Missing organizations/workspaces/assets/assessments/incidents/policies/approvals/workflows/billing/AI-knowledge endpoints | Backend owner |
| Realtime (WebSockets) | Partial | Run-log and notification WebSockets present | Backend owner |

### 5.9 Observability and operations (Blueprint Section 10)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Metrics, structured logging, alerting, backup/recovery | Partial | Prometheus endpoint + JSON logging present; alerting, RPO/RTO, backup automation absent | DevOps owner |

### 5.10 Deployment and infrastructure (Blueprint Section 11)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Dev/Staging/Production topology, network segmentation, secrets, backup | Partial | Dev compose complete; prod compose partial; staging absent; Helm basic | DevOps owner |

### 5.11 Security engineering baseline (Blueprint Section 12)

| Control | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Authentication, authorization, tenancy, secrets, transport, DB, evidence, execution, network, AI, audit, dependencies, containers, CI/CD, recovery | Partial | MFA/TOTP implemented; RBAC partial; tenant isolation missing; TLS/external secrets/encryption-at-rest not configured; runner sandbox missing; audit enforcement partial | Security owner |

### 5.12 Subscription and commercial architecture (Blueprint Section 13)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Editions, entitlements, metering | Missing | No billing/subscription models or endpoints | Product owner |

### 5.13 Quality gates, release criteria, roadmap phases (Blueprint Sections 14-16)

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| Phase 0 baseline exit criteria | In progress | This gap analysis is the Phase 0 deliverable; per-subsystem statuses and owners recorded here | All owners |
| Release criteria (MFA, RBAC, tenancy, runner, scope, AI, evidence, DB, CI, monitoring, recovery) | Partial | MFA and basic security tests present; cross-tenant, runner-containment, evidence-integrity gaps open | Security owner |

## 6. Cross-cutting observations and highest-risk gaps

The blueprint's five review-focus failure modes map to the following live-state
posture:

1. **Cross-tenant authorization regression** - Status: **Not addressed**.
   No organization/workspace/tenant model exists; isolation is implicit via
   per-user engagement ownership. Unresolved high-priority risk.
2. **Runner isolation / scope-enforcement bypass** - Status: **Partial**.
   Scope checks implemented; isolated runner execution and hardened runtime not
   implemented. High-priority risk before any real tool execution.
3. **AI tool-execution policy bypass** - Status: **Partial**. AI suggestions are
   advisory and audited; no policy gate between AI-proposed tool execution and
   execution permission.
4. **Evidence integrity failure** - Status: **Partial**. Evidence rows exist
   without enforced SHA-256 checksum; integrity verification absent.
5. **Untraceable report generation** - Status: **Partial**. Reports bind to
   engagement; traceability fields exist; checksum/approval/audit binding not
   enforced end-to-end.

## 7. Phase 0 exit criteria mapping

Blueprint Phase 0 requires: "Inventory every application, package, endpoint,
table, integration and deployment. Every subsystem has an implementation status
and owner."

- Inventory delivered by this document (Section 4 checklists).
- Gap statuses and owners delivered by Sections 5 and 8.
- Phase 0 remains open until owners are confirmed and remaining gaps are
  dispositioned (implemented / deferred with rationale).

## 8. Owners and next actions

| Subsystem | Status | Accountable owner (next action) | Next action |
| --- | --- | --- | --- |
| Tenant / organization model | Missing | Security owner | Design tenancy hierarchy and migration plan |
| Asset intelligence | Missing | Backend owner | Model assets and relationships |
| Defensive operations (incidents/alerts) | Missing | Security owner | Design defensive domain |
| Policy engine | Missing | Security owner | Define policy model and enforcement |
| Billing / subscriptions | Missing | Product owner | Define entitlement model |
| Runner isolation & hardening | Missing | Security owner | Implement hardened runner execution |
| Reporting formats/compliance | Partial | Backend owner | Add JSON/CSV, compliance mappings |
| Monitoring/alerting/backup | Partial | DevOps owner | Add monitoring stack and recovery runbooks |
| Web navigation/completeness | Partial | Frontend owner | Expand pages per blueprint nav |

## 9. Unverified items

- Whether the API enforces the `success`/`data`/`meta` response envelope
  everywhere (observed: ad-hoc shapes on several endpoints).
- Whether audit logging is append-only at the database level.
- Whether run execution enforces approval before execution (approval model
  exists; execution path not wired).
- Whether JWT transport uses secure, HttpOnly, SameSite cookies with CSRF
  protection (current implementation uses Bearer header).

## 10. Conclusion

The live repository contains a substantial foundation (auth, MFA, RBAC, scope
checks, tool registry, run worker, reporting, observability primitives) but is
substantially short of the blueprint target state across tenancy, asset
intelligence, defensive operations, policy, execution isolation, reporting
formats, and commercial architecture. The gap analysis in this document is the
baseline consumed by Tasks 2-3 of the implementation plan.

---
