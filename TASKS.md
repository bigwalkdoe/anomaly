# Anomaly Task List

_Last updated: 2026-11-10 (post crash-recovery, AI/UI/CLI/docs, gap analysis, and validation pass)_

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
  - **Actions:** re-run Safety/pip-audit in CI, remediate or formally accept dependency findings, and keep Bandit/gitleaks gates green with documented rationale.
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

- [ ] **Implement first production-grade vertical slice with tests**
  - Must cover: cross-tenant authz regression, runner isolation/scope-enforcement bypass, AI tool-execution policy bypass, evidence integrity, and report traceability. (Specification/ADRs prepared; implementation not yet started.)

- [ ] **Introduce tenant model & enforcement (Organization/Workspace)**
  - Additive schema/domain changes; enforce tenant context server-side across API/WS/exports/workers.

- [ ] **Harden execution, evidence, and reporting foundations**
  - Policy-before-execution, runner containment/limits, evidence checksums/provenance, and org/engagement/job/execution-traceable reports.

## P2 — Hardening and hygiene

- [ ] **Harden newly added CLI commands** *(in progress)*
  - **Progress (2026-11-10):** added mocked-HTTP CLI tests covering help/command discovery, config show/set/unset, engagements/findings list, runs start/status, reports generate, and sync status/spectre (`tests/cli/test_commands.py`).
  - **Remaining:** validate against live API contracts/edge cases and expand coverage as needed.

- [x] **Address Pydantic v2 deprecation warnings**
  - **Progress (2026-11-10):** migrated class-based `Config` to `ConfigDict(from_attributes=True)` in `apps/api/src/anomaly_api/schemas/engagement.py` and routers (`api_keys`, `findings`, `playbooks`, `runs`, `schedules`); targeted API AI tests now run without prior Pydantic config deprecation warnings.

- [ ] **Review API/browser security posture**
  - Environment-specific CORS, cookie/CSRF/session hardening, and consistent authz checks on WS/uploads/exports.

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
