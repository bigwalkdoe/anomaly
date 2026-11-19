# Anomaly Task List

_Last updated: 2026-11-19 (tenant/enforcement hardening, schedules/upload RBAC, v1 report endpoint alignment, targeted validation)_

## P0 — Correctness, security, and release blockers

- [x] **Resolve Alembic migration lineage (multiple heads)** *(resolved and validated on clean DB)*
  - **Progress (2026-11-10):** removed duplicate parallel chain from `packages/core/alembic/versions`; generated `00ea86254717_add_login_attempts.py` to resolve schema drift; canonical head is **`00ea86254717`**. Validated on a clean Postgres 16 DB: `alembic upgrade head` and `alembic check` passed (no new operations). Dev DB stamped/upgraded to head with `alembic check` passing.
  - **Remaining:** pre-existing `downgrade base` issue on unnamed FK constraint in historical migrations; continue documenting canonical migration path and verify downgrade strategy on representative environments.

- [x] **Achieve CI lint parity (Python)**
  - **Progress (2026-11-10):** fixed remaining Ruff issues (E501/E402/import cleanup) in tools/tests and migrated Pydantic `class Config` to `ConfigDict` where flagged; `ruff check .` passes.

- [x] **Restore full Python test-suite signal** *(validated in local env)*
  - **Progress (2026-11-10):** targeted broader subset → **68 passed** (~49s). Full `python3 -m pytest -q` completed successfully → **123 passed in 433.05s (0:07:13)**.
  - **Note:** continue monitoring for flakiness/slow tests and ensure CI-equivalent services/env reproducibility.

## P1 — CI parity and quality gates

- [x] **Type checking parity** *(validated)*
  - **Progress (2026-11-10):** fixed initial 3 errors, then re-ran `mypy packages apps` → **Success: no issues found in 103 source files**. (Ruff lint also clean.) Web lint/build previously passed.
  - **Note:** CI-equivalent environment parity still depends on reproducible full-suite and service setup.

- [ ] **Security & dependency CI jobs** *(in progress)*
  - **Progress (2026-11-10):** `docker` runner image build succeeded. `gitleaks` findings triaged (no tracked source secrets; config updated, targeted rescans clean). Bandit hardened/triaged: switched nmap to `defusedxml`, added justified `#nosec` suppressions for intentional defensive patterns and fixed historical migration case; `python3 -m bandit -r packages apps -q` exits 0 with suppressed findings documented in code. `safety check` failed in this environment (tool/runtime issue); `pip-audit` ran and reported environment-wide dependency vulnerabilities (many outside project-managed deps) — requires CI/curated remediation.
  - **Progress (2026-11-17):** restored Bandit gate locally by adding missing justified `#nosec B110` in `apps/api/src/anomaly_api/routers/v1_slice.py` inline-run path (`python3 -m bandit -r packages apps -q` exits 0). Re-ran `python3 -m pip_audit` (env audit) and observed 122 reported vulns across 14 installed packages (largely tooling/global env deps such as `aiohttp`, `pillow`, `poetry`, `uv`, `virtualenv`, `dulwich`, etc.); project-scoped/curated remediation and CI-safe Safety/pip-audit execution remain required.
  - **Progress (2026-11-17, follow-up):** `gitleaks detect --source . --no-banner --redact` reported no leaks (exit 0). Project-scoped dependency audit via `uv export --format requirements-txt --all-packages` + `python3 -m pip_audit -r ...` found no known vulnerabilities in auditable third-party deps (exit 0; local workspace packages skipped as not on PyPI).
  - **Progress (2026-11-17, CI wiring):** updated `.github/workflows/ci.yml` to enforce Bandit on `packages apps` and run project-scoped `pip-audit` against `uv export`ed dependencies (artifacts uploaded); Safety retained as best-effort/informational against exported deps. CI execution still pending in GitHub runners.
  - **Actions:** validate the updated CI jobs in CI, remediate or formally accept any reported dependency findings, and keep Bandit/gitleaks gates green with documented rationale.
  - **Done when:** jobs run clean or with documented, approved exceptions.

- [x] **Runner image build validation**
  - **Progress (2026-11-10):** `docker build -t anomaly-runner:dev infra/runner` completed successfully.

- [ ] **Comprehensive runtime visual/functional QA (web)** *(smoke completed)*
  - **Progress (2026-11-10):** Playwright smoke against production build (`next start`) captured `/login`, `/register`, and not-found in light/dark (`.playwright-mcp/*`).
  - **Remaining:** authenticated routes/data states, theme toggle/persistence, contrast/accessibility, responsive behavior, error/loading/empty states, and automation of critical flows against a running API.
  - **Done when:** checklist of core routes/states reviewed in light/dark with issues filed/fixed.

## P1 — Blueprint-driven platform work (from gap analysis)

- [x] **Finalize ADRs 001–012** (`docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`)
  - **Progress (2026-11-10):** replaced section 18 summary table with finalized ADR catalogue (ADR-001–ADR-012) covering product scope, architecture, stack, data stores, authn, tenancy/authz, policy/approvals, execution isolation, evidence/report traceability, AI governance, events/contracts, and observability/deployment/commercial, including consequences and migration impact.

- [x] **Create implementation spec + prioritized backlog for first vertical slice**
  - **Progress (2026-11-10):** added `docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md` defining the governed E2E slice, additive data model/service/API/event contracts, security controls, test plan, and prioritized backlog (B-001…B-020).

- [ ] **Implement first production-grade vertical slice with tests** *(in progress — tenancy propagation and API wiring started)*
  - **Progress (2026-11-10):** added tenancy foundations (B-003/B-004): `Organization`/`OrganizationMember` models, `packages/core/src/anomaly_core/tenancy.py`, and additive `organization_id` propagation to `engagements`, `runs`, `findings`, `evidence`, `reports`, `audit_logs`, `approvals` (+ `approvals.engagement_id`) with migrations `ab12cd34ef56` and `cd34ef56ab78` (head `cd34ef56ab78`, `alembic check` clean). Wired `organization_id` through engagement create/response and audit logging (`AuditService.log`), and propagated org context to run creation/audit records; targeted API/CLI/AI tests passing.
  - **Progress (2026-11-19):** aligned v1 slice report generation contract additively — `apps/api/src/anomaly_api/routers/v1_slice.py` now shares report-generation implementation for `GET /api/v1/engagements/{id}/reports/generate` (preserved) and `POST /api/v1/engagements/{id}/reports` (accepts body/query `format`, default `markdown`). Targeted lint checks passed.
  - **Remaining:** server-side org context/enforcement across all API/services/WS/exports (cross-tenant tests), approvals + policy decision service/hooks, policy-gated scope-validated isolated execution manifests/containment, findings normalization linkage, evidence integrity/provenance (checksums, immutable metadata), traceable reporting, and required security tests (cross-tenant, runner/scope bypass, AI execution-policy bypass, evidence/report traceability).

- [ ] **Introduce tenant model & enforcement (Organization/Workspace)**
  - Additive schema/domain changes; enforce tenant context server-side across API/WS/exports/workers.
  - **Progress (2026-11-19):** hardened engagement access semantics to avoid existence leakage in `apps/api/src/anomaly_api/deps.py` (`require_engagement_access`: 404 for non-viewer/non-member/cross-tenant, 403 only for known members with insufficient role). Aligned schedules routes (`apps/api/src/anomaly_api/routers/schedules.py`) to no-leak 404s and enforced `pentester` role for schedule create/delete (list remains viewer-accessible). Restricted legacy and v1 report generation to `pentester+` with no-leak checks (`apps/api/src/anomaly_api/routers/reports.py`, `apps/api/src/anomaly_api/routers/v1_slice.py`). Updated `tests/api/test_rbac.py` expectations for non-member/unassigned access. Verified: `python3 -m pytest tests/api/test_rbac.py::test_client_viewer_no_runs_and_no_create tests/api/test_rbac.py::test_pentester_can_access_assigned_engagements_only tests/api/test_rbac.py::test_unassigned_user_gets_403_on_engagement_endpoints -q` (3 passed), `python3 -m pytest tests/api/test_tenancy_isolation.py::test_cross_tenant_authorization_regression -q` (1 passed), `python3 -m pytest tests/api/test_schedules.py -q` (1 passed), and `ruff check` on touched files.
  - **Remaining (tomorrow):** continue auditing all remaining mutation/read surfaces for consistent min-role + no-leak enforcement (legacy report generation permissions, evidence/report/export/admin/aggregate/WS/worker paths as applicable), extend cross-tenant tests for any newly hardened surfaces, and centralize/align assessment-request policy gate + enqueue flow across `runs.py`, `v1_slice.py`, and `playbooks.py` (including worker/scheduler re-validation before execution). Re-run broader DB-backed/API subsets and CI-runner checks when environment is stable.

- [ ] **Harden execution, evidence, and reporting foundations**
  - Policy-before-execution, runner containment/limits, evidence checksums/provenance, and org/engagement/job/execution-traceable reports.

## P2 — Hardening and hygiene

- [ ] **Harden newly added CLI commands** *(in progress)*
  - **Progress (2026-11-10):** added mocked-HTTP CLI tests covering help/command discovery, config show/set/unset, engagements/findings list, runs start/status, reports generate, and sync status/spectre (`tests/cli/test_commands.py`).
  - **Progress (2026-11-16):** hardened CLI command modules (`apps/cli/src/anomaly_cli/commands/*`) with consistent request timeouts/error handling (network/HTTP/invalid JSON), defensive response parsing, empty findings-update payload handling (`{}`), and sync-spectre failure reporting; expanded `tests/cli/test_commands.py` with edge-case coverage (HTTP/network errors, invalid params/context, missing fields, partial sync failures). Validated against current API router contracts for engagements/findings/runs/reports/AI/dashboard endpoints; CLI tests pass (15) and Ruff clean on touched files.
  - **Remaining:** validate against a live running API environment (end-to-end) and continue expanding coverage for additional commands/flows as they evolve.

- [x] **Address Pydantic v2 deprecation warnings**
  - **Progress (2026-11-10):** migrated class-based `Config` to `ConfigDict(from_attributes=True)` in `apps/api/src/anomaly_api/schemas/engagement.py` and routers (`api_keys`, `findings`, `playbooks`, `runs`, `schedules`); targeted API AI tests now run without prior Pydantic config deprecation warnings.

- [ ] **Review API/browser security posture** *(in progress)*
  - **Progress (2026-11-16):** made CORS environment-specific (`ANOMALY_CORS_ORIGINS`/`CORS_ALLOW_ORIGINS`, credentials disabled for wildcard), hardened upload handling (filename sanitization, configurable max size), removed duplicate no-op logout route and fixed `/api/auth/verify` to require/validate Bearer tokens; reviewed WS/upload/export surfaces (WS run/notification endpoints authenticate tokens and enforce access checks; upload requires engagement access; no dedicated export endpoints found). Auth uses Bearer tokens (not cookies), so CSRF exposure is currently limited.
  - **Progress (2026-11-17):** hardened webhook stub (`/api/webhooks` admin-only; create returns 501 not implemented) and added configurable metrics protection (`ANOMALY_METRICS_AUTH_REQUIRED` requires authenticated admin when enabled; default unchanged).
  - **Progress (2026-11-19):** tightened evidence upload authorization — `POST /api/upload/engagements/{id}` now requires `pentester` engagement role (`apps/api/src/anomaly_api/routers/upload.py`), in addition to prior filename/size hardening.
  - **Remaining:** add/validate security headers and session/cookie hardening if cookies are introduced, confirm WS origin/proxy/logging posture for token-in-query, and expand automated checks for WS/upload/auth edge cases in CI-like environments.

- [x] **Migration/tooling hygiene** *(partial)*
  - **Progress (2026-11-10):** removed duplicate parallel Alembic chain files from `packages/core/alembic/versions`, leaving single head `f6b770b737bd`. Additional cleanup may be needed for duplicate revisions in worktrees/copies and DB stamp/sync.

## Recently completed (reference)

- [x] AI suggest-tools: core settings, real providers, structured/audited `suggest_tools`, API endpoint, CLI command, targeted tests/lint, docs/spec/plan.
- [x] Enterprise UI updates across web surfaces reconciled and committed; web build/typecheck pass.
- [x] CLI command modules added and entrypoint streamlined.
- [x] DB fixture teardown stabilized for API/core (`DROP SCHEMA ... CASCADE`); `tests/api/test_ai.py` passes.
- [x] `uv.lock` tracked.
- [x] Web lint fix in `apps/web/app/findings/[id]/page.tsx`.
- [x] Blueprint gap analysis added (`docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md`).
- [x] Validation pass: subset tests (64 passed), web lint/build, Alembic lineage/DB-state diagnosis, Playwright theme smoke (login/register/not-found).
- [x] Tasklist execution pass (2026-11-10): `ruff check .` clean, Alembic canonical head resolved (duplicate chain removed), targeted subset now **68 passed** (`tests/ai tests/api/test_ai.py tests/cli tests/core tests/tools tests/reporting`), Pydantic v2 config deprecations addressed, `docker build -t anomaly-runner:dev infra/runner` succeeded, and initial mypy errors in touched files fixed (full `mypy packages apps`/CI parity and DB migration sync still pending). 
