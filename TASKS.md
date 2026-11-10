# Anomaly Task List

_Last updated: 2026-11-10 (post crash-recovery, AI/UI/CLI/docs, gap analysis, and validation pass)_

## P0 — Correctness, security, and release blockers

- [x] **Resolve Alembic migration lineage (multiple heads)** *(partially validated)*
  - **Progress (2026-11-10):** removed duplicate parallel chain (`54816ee86f69`, `6bdfa4300d23`, `2b6309618aaf`, `b07b80459ce9`) from `packages/core/alembic/versions`; `alembic heads` now reports single head `f6b770b737bd (head)`.
  - **Remaining:** local DB was not up to date and `alembic upgrade head` failed on existing schema (`relation "permissions" already exists`) — DB needs stamp/rebuild/sync against canonical head in this environment; verify `upgrade head`/`downgrade` on a representative clean DB and document canonical path.

- [x] **Achieve CI lint parity (Python)**
  - **Progress (2026-11-10):** fixed remaining Ruff issues (E501/E402/import cleanup) in tools/tests and migrated Pydantic `class Config` to `ConfigDict` where flagged; `ruff check .` passes.

- [ ] **Restore full Python test-suite signal**
  - **Progress (2026-11-10):** targeted broader subset `pytest tests/ai tests/api/test_ai.py tests/cli tests/core tests/tools tests/reporting -q` → **68 passed** (~49s). Full `pytest -q` previously timed out (>120s) locally.
  - **Actions:** run full suite with CI-equivalent services/env, identify slow/hanging/flaky tests, split/mark integration tests appropriately, and stabilize.
  - **Done when:** full suite completes reliably with expected pass/skip behavior.

## P1 — CI parity and quality gates

- [ ] **Type checking parity** *(in progress)*
  - **Progress (2026-11-10):** `mypy packages apps` reported 3 errors in 103 files; fixed `apps/cli/src/anomaly_cli/commands/runs.py`, `packages/tools/src/anomaly_tools/registry.py`, and `packages/ai/src/anomaly_ai/service.py`. Targeted `mypy` on fixed files passes; full CI-parity run not yet revalidated.
  - **Actions:** re-run `mypy packages apps`, address remaining config/typing gaps incrementally.
  - **Done when:** `mypy packages apps` passes (or agreed baseline enforced).

- [ ] **Security & dependency CI jobs** *(in progress)*
  - **Progress (2026-11-10):** `docker` runner image build succeeded (`docker build -t anomaly-runner:dev infra/runner`). `gitleaks detect --source . --no-git -v` attempt timed out (>120s) in this environment. `bandit`/`safety` CLI modules not installed locally.
  - **Actions:** run/triage `bandit`, `safety`, and complete `gitleaks` scan in CI or with adequate time/tools; remediate or document accepted risks.
  - **Done when:** jobs run clean or with documented, approved exceptions.

- [x] **Runner image build validation**
  - **Progress (2026-11-10):** `docker build -t anomaly-runner:dev infra/runner` completed successfully.

- [ ] **Comprehensive runtime visual/functional QA (web)** *(smoke completed)*
  - **Progress (2026-11-10):** Playwright smoke against production build (`next start`) captured `/login`, `/register`, and not-found in light/dark (`.playwright-mcp/*`).
  - **Remaining:** authenticated routes/data states, theme toggle/persistence, contrast/accessibility, responsive behavior, error/loading/empty states, and automation of critical flows against a running API.
  - **Done when:** checklist of core routes/states reviewed in light/dark with issues filed/fixed.

## P1 — Blueprint-driven platform work (from gap analysis)

- [ ] **Finalize ADRs 001–012** (`docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`)
  - Decisions, trade-offs, and migration consequences (tenancy, policy engine, runner isolation, evidence integrity, AI action gating, etc.).

- [ ] **Create implementation spec + prioritized backlog for first vertical slice**
  - Governed E2E flow: authenticate → create engagement → scope → approval → policy/scope validation → isolated execution → normalized findings → preserved evidence → traceable report.

- [ ] **Implement first production-grade vertical slice with tests**
  - Must cover: cross-tenant authz regression, runner isolation/scope-enforcement bypass, AI tool-execution policy bypass, evidence integrity, and report traceability.

- [ ] **Introduce tenant model & enforcement (Organization/Workspace)**
  - Additive schema/domain changes; enforce tenant context server-side across API/WS/exports/workers.

- [ ] **Harden execution, evidence, and reporting foundations**
  - Policy-before-execution, runner containment/limits, evidence checksums/provenance, and org/engagement/job/execution-traceable reports.

## P2 — Hardening and hygiene

- [ ] **Harden newly added CLI commands**
  - Validate `config/engagements/findings/reports/runs/sync` against real API contracts; add mocked-HTTP tests for key flows.

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
