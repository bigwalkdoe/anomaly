# Anomaly Full Platform Gap Analysis

**Date:** 2026-11-10  
**Spec:** `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`  
**Plan:** `docs/superpowers/plans/2026-11-10-anomaly-full-platform-design-blueprint.md` (Task 1)  
**Baseline branch/HEAD reviewed:** `main` @ `23764dc` (working tree included crash-recovery commits for AI/UI/CLI/docs; `uv.lock` untracked at time of analysis)

> **Important qualification:** This is an implementation-vs-target-state inventory based on repository inspection (code, configs, docs, tests). It does **not** constitute a completed source-code audit, penetration test, runtime verification of all integrations, or production-readiness certification. Items marked **unverified** require execution in a representative environment.

## 1. Executive summary

Anomaly currently implements a **modular monolith-style API + web UI + CLI + worker/tooling foundations** oriented around engagements, scope entries, targets, runs, findings, evidence/reporting primitives, and basic RBAC/membership controls. Recent work added **AI provider configuration and advisory `suggest-tools`** (audited) and an **enterprise UI** pass across core screens.

Relative to the blueprint’s target state (governed security operations control plane with strong multi-tenancy, isolated execution, policy engine, asset/vulnerability/incident lifecycles, evidence integrity, and AI-governed automation), the repo is **early/partial**: core domain primitives exist, but **organization/workspace tenancy, approvals/policy engine, execution isolation/containment guarantees, evidence integrity/provenance, and end-to-end governed vertical-slice flows** are not yet fully realized or verified.

## 2. Repository inventory (live baseline)

### 2.1 Applications
| Component | Path | Status | Notes |
|---|---|---|---|
| API (FastAPI) | `apps/api` | **Partial** | Rich router set (`health, auth, engagements, findings, runs, audit, users, stats, dashboard, tags, webhooks, ws, playbooks, upload, search, notifications, evidence, api_keys, metrics, mfa, schedules, reports, vulnerabilities, ai`); centralized startup RBAC seeding; permissive CORS (`*`). |
| Web (Next.js/TS) | `apps/web` | **Partial** | App routes for dashboard/auth/engagements/findings/runs/reports/playbooks/schedules/settings; enterprise UI updates committed; runtime cross-theme QA still recommended. |
| CLI (Typer/Rich) | `apps/cli` | **Partial** | Command groups wired (`ai, config, dashboard, engagements, findings, reports, runs, sync`) plus `auth-login`, `version`; API-contract alignment/tests limited. |
| Worker | `apps/worker` | **Partial / Unverified** | `src/anomaly_worker/{main,executor,tasks}.py` present; actual queue/orchestration/runtime behavior not fully verified here. |

### 2.2 Packages
| Package | Path | Status | Notes |
|---|---|---|---|
| Core domain/config/db/auth/rbac/scope/runner | `packages/core` | **Partial** | SQLAlchemy async models and enums, JWT auth helpers, RBAC seeding/permission checks, engagement-scope checking, runner protocol (`RunSpec/RunResult`, `FakeRunner`, basic `DockerRunner` shell), Alembic migrations present. |
| AI providers/service | `packages/ai` | **Partial** | Real HTTP providers (Ollama/OpenAI/Anthropic via `httpx`), structured/audited `suggest_tools`, `complete/draft_*`; advisory only (no execution). |
| Tool registry/adapters | `packages/tools` | **Partial** | Registry + tools (`stub,nmap,httpx,recon,nuclei,ffuf,sqlmap`); adapter isolation/normalization/error taxonomy not fully verified. |
| Reporting | `packages/reporting` | **Partial / Unverified** | `generator.py`, `templates.py` present; traceability/integrity/format guarantees unverified. |
| Integrations | `packages/integrations` | **Missing / Unverified** | Package exists; concrete integrations/capabilities not assessed in depth. |
| Common | `packages/common` | **Unverified** | Present; contents/use not deeply inventoried. |

### 2.3 Data & migrations
| Component | Path | Status | Notes |
|---|---|---|---|
| PostgreSQL schema/models | `packages/core/src/anomaly_core/models/*` | **Partial** | Entities include users/tokens/memberships/MFA/login attempts, engagements/scopes/targets, runs, findings/evidence (in models), playbooks/steps, approvals, cron schedules, audit; **no explicit Organization/Workspace hierarchy** observed. |
| Alembic migrations | `packages/core/alembic/versions/*` | **Partial / Unverified** | Multiple revision files exist (including duplicates/parallel-looking histories in tree/worktrees); migration lineage/health against current models **unverified**. |
| Redis / MinIO / search stores | `docker-compose.yml`, API upload usage implied | **Partial / Unverified** | Compose provides Postgres/Redis/MinIO; runtime wiring (queues, evidence storage paths/checksums, search indexing) **unverified**. |

### 2.4 Infrastructure & operations
| Component | Path | Status | Notes |
|---|---|---|---|
| Local compose | `docker-compose.yml` | **Partial** | Postgres 16, Redis 7, MinIO; no API/worker/web runner services defined here. |
| Prod compose | `docker-compose.prod.yml` | **Unverified** | Present; contents not fully reviewed. |
| Service Dockerfiles | `infra/{api,runner,tools,web,worker}` | **Partial / Unverified** | Directories exist; build/runtime hardening and isolation guarantees unverified. |
| CI / quality gates | `.github/` | **Unverified** | Present; enforcement of blueprint quality gates unknown. |
| Deployment docs | `docs/DEPLOYMENT_GUIDE.md`, `SECURITY.md` | **Partial** | Documentation exists; alignment with target-state controls unverified. |

### 2.5 Tests (observed)
| Area | Path | Status | Notes |
|---|---|---|---|
| AI | `tests/ai/test_ai.py` | **Implemented (targeted)** | Provider/service/suggest-tools behavior covered with mocks; passed in recovery verification. |
| API (AI) | `tests/api/test_ai.py` | **Implemented** | Auth/structured/fallback/engagement-access cases; DB setup/teardown stabilized for this env (`DROP SCHEMA public CASCADE` in fixtures). |
| CLI | `tests/cli/test_cli.py`, `tests/cli/test_ai_cli.py` | **Partial** | Version + AI suggest-tools covered; other command modules lightly/uncovered. |
| Core/API/Tools broad suites | `tests/core`, `tests/api`, `tests/tools`, etc. | **Unverified** | Not fully executed in this pass. |

## 3. Blueprint component mapping

Statuses: **Implemented** (present and materially aligned), **Partial** (exists but incomplete/misaligned), **Missing**, **Deprecated** (not observed), **Unverified**.

| Blueprint area | Current status | Evidence (representative) | Gap / notes | Owner / next action |
|---|---|---|---|---|
| **1. Product definition / control plane** | Partial | Engagement/run/finding/evidence/report primitives; AI advisory suggestions; dashboards/stats/search routes exist | Not yet a unified governed SecOps control plane; asset/vuln/incident lifecycles and governance flows incomplete | **Product/Arch:** define scoped MVP capabilities per slice; track via blueprint backlog |
| **2. Target-state architecture (modular monolith + isolated workers/runners)** | Partial | FastAPI app + routers; `packages/core.runner` protocol + `DockerRunner` stub-ish behavior; `apps/worker` present; Redis/MinIO in compose | API/worker/runner boundaries and isolation not enforced/verified end-to-end; event contracts/jobs not fully documented | **Platform:** harden job orchestration + runner isolation ADR/impl |
| **2.1 Principles: centralized identity/authz, scope validation, AI no policy bypass, no tool exec in API, scoped workers, evidence traceability, audit events, versioned contracts** | Partial | JWT + RBAC/membership deps; `scope.check_scope`; AI suggestions audited/advisory; audit router/log model present | Enforcement consistency across APIs/WS/exports/workers **unverified**; scope is warn/log oriented in places; evidence integrity/traceability incomplete; contracts undocumented | **Security/Platform:** policy enforcement matrix + tests per principle |
| **3.1 Workspace dashboard** | Partial | `dashboard`/`stats` routers; web dashboard page | Metrics derivation, filters, and real-time/system-health semantics **unverified** | **Web/API:** align metrics definitions + add tests |
| **3.2 Asset intelligence & lifecycle** | Missing / Partial | `Target` model/types/status (`active/discovered/confirmed`) exist | No full asset inventory/relationships/observations/lifecycle (DISCOVERED→…→ARCHIVED) as specified | **Core/Domain:** asset model + lifecycle + inventory APIs |
| **3.3 Vulnerability management** | Partial | Findings model/router; vulnerabilities router/summary implied | No full CVE/CWE/CVSS+business-risk, dedupe, remediation workflow, exceptions/risk acceptance, reassessment/trends as first-class | **Core/API:** normalize vuln/finding domain + workflows |
| **3.4 Offensive security operations (adapters, normalization, scope, audit)** | Partial | Tool registry/adapters in `packages/tools`; runs API/worker scaffolding; scope checks exist | Per-adapter versioning, structured I/O normalization, timeouts/limits/error taxonomy, and strict policy-driven authorization **unverified/incomplete** | **Tools/Runner:** adapter contract + execution policy enforcement |
| **3.5 Defensive monitoring & incident management** | Missing / Partial | No dedicated incident/alert/event ingestion domain observed in core inventory | Blueprint’s detection/incident flows largely absent | **Domain/API:** incident/event models and pipelines (separate from runner) |
| **3.6 AI intelligence** | Partial | `packages/ai` providers + audited `suggest_tools`/draft methods; AI router/CLI | Retrieval, structured action proposals with policy gating, usage controls, and broader AI workflows per blueprint **missing/unverified**; AI must not bypass policy (advisory only today) | **AI/Platform:** policy-gated AI actions + evaluation/controls |
| **3.7 Engagement management & lifecycle** | Partial | Engagement CRUD/modes/status (`draft/active/paused/closed`), scope/targets/memberships | Missing `PENDING_APPROVAL/APPROVED/COMPLETED/ARCHIVED` lifecycle, approvals workflow, permitted assessment types/limits/retention fields as specified | **Core/API:** extend engagement lifecycle + approvals |
| **3.8 Evidence management (first-class, integrity, provenance)** | Partial | Evidence model/router/upload present; runs/findings linkage implied | SHA-256 checksums, immutable provenance (org/engagement/job/execution/collector/tool version), access/retention/versioning guarantees **unverified/incomplete** | **Core/Storage:** evidence integrity + provenance schema/contracts |
| **3.9 Reporting & compliance** | Partial | `packages/reporting`, reports router/CLI flows exist | Traceability to org/engagement/job/execution, format guarantees (PDF/HTML/MD/JSON/CSV), versioned compliance mappings **unverified/incomplete** | **Reporting:** traceable report pipeline + tests |
| **4. Identity, tenancy, authorization** | Partial | Users/roles/permissions, RBAC seeding, memberships, engagement access checks; auth/MFA/API keys routes; cookie/session considerations implied | **No Organization/Workspace hierarchy or tenant-context enforcement as specified**; OIDC/SAML/CSRF/session hardening and resource-level checks across WS/exports **unverified**; client-supplied tenancy must be rejected (verify) | **Security:** tenant model + consistent authz boundary |
| **4.1 Roles/permissions model** | Partial | `admin/pentester/client_viewer` roles and permission seeds | Blueprint’s expanded role set (Platform/Org/Sec Admin, Analyst, IR, Auditor, Viewer) and fine-grained permissions not fully implemented | **Security/Core:** expand RBAC model/migrations compatibly |
| **5. Data architecture** | Partial | Postgres models + Alembic; Redis/MinIO in compose; JSON fields on runs/params | Dedicated entities for orgs/workspaces/assets/relationships/vuln records/CVEs/incidents/alerts/events/policies/decisions/ai sessions/usage/billing/search indexing **largely missing or unverified** | **Data/Arch:** incremental schema evolution per slice |
| **6. Backend architecture** | Partial | Service-layered FastAPI routers, deps, middleware (request id/rate limit/validation handlers) | Documented module interfaces, domain/application/service/repository boundaries, and versioned internal contracts **incomplete/unverified** | **Platform:** boundary refactors guided by ADRs |
| **7. Execution engine & isolation** | Partial | Runner protocol, tool registry, worker app; scope checks before runs (intended) | Strong isolation (no API-process exec), scoped worker identities, resource limits/timeouts/network controls, and enforcement correctness **unverified/incomplete** (`DockerRunner` minimal) | **Runner/Security:** enforce isolated execution + containment tests |
| **8. Frontend & UX blueprint** | Partial | Core authenticated routes/screens, enterprise UI styling pass, build passes | Real-time ops views, filters, accessibility/contrast runtime QA, and full blueprint UX coverage **partial/unverified** | **Web:** iterate per product slices |
| **9. API architecture** | Partial | REST endpoints + OpenAPI tags/docs, WS router present | Versioned API/event contracts, consistent error/pagination/filter semantics, tenant-safe access on all surfaces **unverified** | **API:** contract hardening + compatibility policy |
| **10. Observability & operations** | Partial | Health/metrics routes present | Structured logging/metrics/tracing, job/system health signals, audit/event observability **unverified** | **SRE/Platform:** observability baseline |
| **11. Deployment & infrastructure** | Partial | Compose (dev), infra Dockerfile dirs, deployment docs | Production topology, secrets management, backups/restore, environment promotion, runner isolation in deploy **unverified** | **DevOps:** document + validate deploy path |
| **12. Security engineering baseline** | Partial | RBAC, scoped engagement access patterns, audited AI suggestions, scope checks, gitleaks/pre-commit config | CORS is permissive; CSRF/session hardening, secret handling, supply-chain controls, least privilege, and end-to-end policy enforcement **unverified** | **Security:** threat-model-driven hardening backlog |
| **13. Subscription & commercial architecture** | Missing / Unverified | No clear plans/subscriptions/usage/billing enforcement observed in core inventory | Quotas, entitlements, usage metering, billing entities **missing** | **Product/Platform:** define if/when in-scope; ADR |
| **14. Implementation roadmap** | Partial | Blueprint plan + this gap analysis; incremental commits exist | Sequenced delivery/backlog issues not yet fully instantiated | **Eng mgmt:** convert to tracked issues |
| **15. Repository restructuring** | Partial | Monorepo-like layout (`apps/*`, `packages/*`, `infra/*`, `docs/*`) exists | Alignment to target boundaries/naming and cleanup of legacy/duplicated artifacts **ongoing/unverified** | **Platform:** incremental refactors only |
| **16. Quality gates & release criteria** | Partial | Some tests/lint/build checks runnable; security hooks configured | Blueprint-grade gates (authz/isolation/evidence/report traceability) not fully automated/enforced | **QA/Security:** define CI gates per slice |
| **17. First production-grade vertical slice** | Missing | Primitives exist (auth, engagement, scope, runs, findings, evidence/report modules) but not integrated as governed E2E flow | Missing: approval/audited policy validation, strict authorization+scope at execution, isolated runner guarantees, normalized findings with integrity, traceable report | **Cross-functional:** implement per Tasks 3–4 of blueprint plan |
| **18. Final architectural decisions (ADRs 001–012)** | Missing / Partial | Blueprint ADR catalogue referenced in spec | ADRs not finalized in-repo as decided records with migration consequences | **Arch:** Task 2 |
| **19. Blueprint acceptance checklist** | Partial | This gap analysis addresses baseline inventory/mapping requirement | Checklist not fully satisfied (ADRs, impl spec/backlog, verified slice, gates) | **Arch/PM:** track to closure |
| **20. Implementation next steps** | Partial | Plan Task 1 completed by this document | Tasks 2–4 pending | **Arch/Platform:** proceed sequentially |

## 4. Cross-cutting gaps and risks (prioritized)

| Priority | Gap | Risk / impact | Recommended action | Owner |
|---|---|---|---|---|
| P0 | No explicit **Organization/Workspace** tenant model & enforcement | Cross-tenant data exposure/regression vs blueprint intent | Introduce tenant entities + propagate tenant context through authz/data access/WS/exports (additive) | Security/Core/API |
| P0 | **Execution isolation & scope/policy enforcement** not verified end-to-end | Unauthorized or out-of-scope execution; runner breakout/abuse | Harden runner/worker boundaries, enforce policy-before-exec, containment/resource limits, tests | Runner/Security |
| P0 | **Evidence integrity/provenance** incomplete | Unverifiable or tamper-prone evidence; weak auditability | Add checksums, immutable metadata (org/engagement/job/execution/tool version), access logging | Core/Storage |
| P0 | **Approvals/policy engine** absent | Ungoverned actions; AI/tool execution not policy-gated as required | Model approvals/policy decisions; gate sensitive operations | Core/API/Security |
| P1 | **Asset/vulnerability/incident** domains below target fidelity | Limited operational value; weak correlation/prioritization | Implement minimal lifecycles needed for first slice, then expand | Domain teams |
| P1 | **Report traceability** to org/engagement/job/execution | Non-defensible outputs | Enforce provenance links and deterministic generation inputs | Reporting/API |
| P1 | Alembic/migration lineage clarity | Drift and unsafe deploys | Audit/clean revision graph, verify upgrade/downgrade paths | Core/DB |
| P1 | Permissive **CORS** and unverified web/session/CSRF hardening | Browser-based abuse in non-dev contexts | Environment-specific CORS/origins, cookie/CSRF posture review | API/Web/Security |
| P2 | Test coverage gaps (CLI modules, broad API/core/tools, integration/E2E) | Regressions in critical paths | Add slice-focused and contract tests; CI gating | QA/Eng |
| P2 | Observability, SLOs, and operational runbooks | Hard to detect/respond to failures | Baseline logs/metrics/traces and health signals | SRE/Platform |

## 5. Blueprint review-focus failure modes (must be covered by first vertical slice)

1. **Cross-tenant authorization regression** — not yet demonstrably prevented by tenant model/enforcement.  
2. **Runner isolation or scope-enforcement bypass** — partial controls exist; isolation/strict enforcement **unverified**.  
3. **AI tool-execution policy bypass** — AI is advisory today (good), but future actioning must be policy-gated.  
4. **Evidence integrity failure** (checksum/provenance/traceability) — incomplete.  
5. **Report generation not traceable** to organization/engagement/job/execution — unverified/incomplete.

## 6. Recommended next actions (accountable)

| # | Action | Deliverable | Owner | Depends on |
|---|---|---|---|---|
| 1 | Finalize ADRs 001–012 with trade-offs/migration impact | Updated ADR catalogue in spec | Architecture | This gap analysis |
| 2 | Define implementation spec + prioritized, mergeable backlog for **first vertical slice** | Impl spec doc + GitHub issues | Architecture + Eng leads | ADRs |
| 3 | Implement governed vertical slice E2E (auth → engagement → scope → approval → policy/scope validation → isolated execution → normalized findings → preserved evidence → traceable report) with tests for 5 failure modes | Code + migrations + tests | Cross-functional (API/Core/Runner/AI/Reporting/Web) | Impl spec |
| 4 | Stabilize DB/migrations and broaden automated test gates (authz, scope, isolation, evidence, reporting) | CI-enforced checks | Platform/QA/Security | Ongoing |
| 5 | Resolve hygiene items: track/decide `uv.lock`, tighten CORS/config per env, complete CLI contract tests | Small PRs | Eng | Now/parallel |

---

*Prepared as Task 1 of the blueprint implementation plan; to be revised as ADRs are finalized and implementation evidence is collected.*
