# Anomaly Full Platform Design Blueprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Anomaly Full Platform Design Blueprint into an incremental implementation backlog and deliver the first production-grade vertical slice.

**Architecture:** The blueprint prescribes a modular monolith control plane with isolated execution services. Implementation proceeds incrementally along the blueprint's recommended execution sequence — baseline inventory, gap analysis, ADR finalization, implementation specification, execution and verification — while preserving existing working functionality and prioritizing security correctness, tenant isolation, scope enforcement and execution containment.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis + ARQ, MinIO, Next.js + TypeScript, Docker.

**Spec:** `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`

## Global Constraints

- The blueprint is a target-state design; implementation must be reconciled against the live repository before execution.
- Preserve existing working functionality; prefer additive migrations and incremental refactoring.
- No destructive restructuring or staging deployment changes before backups are verified and the current environment is documented.

## Review Focus

Five input classes or failure modes the blueprint implies but no task's tests exercise that are most likely to bite a person using this software:

1. Cross-tenant authorization regression in the delivered vertical slice.
2. Runner isolation or scope-enforcement bypass in delivered slice work.
3. AI tool-execution policy bypass in delivered slice work.
4. Evidence integrity failure (checksum mismatch or untraceable evidence) in delivered slice work.
5. Report generation that is not traceable to organization, engagement, job and execution.

## Tasks

### Task 1: Baseline repository inventory and gap analysis

**Files:**
- Create: `docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md` (deliverable)

**Interfaces:**
- Consumes: the blueprint spec (`docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md`) and the live repository.
- Produces: a gap-analysis document mapping each blueprint component to a current status (implemented / partial / missing / deprecated / unverified) with an accountable owner.

- [ ] **Step 1: Inventory live repository components**

Produce a checklist of every application, package, endpoint, table, integration and deployment relevant to the blueprint domains.

- [ ] **Step 2: Map implementation against blueprint**

Write the gap analysis, labeling each blueprint component and recording owners for next actions.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-11-10-anomaly-full-platform-design-blueprint.md docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md
git commit -m "docs: add blueprint gap analysis"
```

### Task 2: Finalize architecture decision records

**Files:**
- Modify: `docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md` (ADR catalogue)

**Interfaces:**
- Consumes: blueprint ADR catalogue and Task 1 gap analysis.
- Produces: finalized ADRs 001–012 with explicit trade-offs and migration consequences.

- [ ] **Step 1: Draft ADRs 001–012**

Write each ADR with decision, context, consequences and migration impact.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md
git commit -m "docs: finalize blueprint ADRs"
```

### Task 3: Define implementation specification and prioritized backlog

**Files:**
- Create: `docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md` (deliverable)

**Interfaces:**
- Consumes: finalized ADRs and Task 1 gap analysis.
- Produces: implementation specification with exact files, migrations, interfaces, API contracts and event schemas, plus a prioritized GitHub issue backlog.

- [ ] **Step 1: Write implementation specification**

Document exact files, migrations, interfaces, API contracts and tests for the first delivery slice.

- [ ] **Step 2: Create prioritized backlog issues**

Create small, independently mergeable GitHub issues with clear acceptance criteria.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md
git commit -m "docs: add blueprint implementation specification and backlog"
```

### Task 4: Deliver first production-grade vertical slice

**Files:**
- Modify: FastAPI API, application services, domain logic, repository interfaces, infrastructure adapters, PostgreSQL/Redis/MinIO.
- Modify: Next.js web app where slice UX is in scope.
- Test: cross-tenant, authorization, scope, runner-isolation and evidence-integrity coverage.

**Interfaces:**
- Consumes: finalized ADRs, implementation specification, prioritized backlog.
- Produces: end-to-end flow — authenticate → create engagement → scope → approval → authorization/scope validation → isolated runner execution → normalized findings → preserved evidence → generated report.

- [ ] **Step 1: Write failing tests for the slice**

Write slice tests covering: authentication, engagement creation, approval auditing, policy validation, isolated execution, findings, evidence and report generation; including the five Review Focus failure modes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -v`
Expected: FAIL for unimplemented slice behavior.

- [ ] **Step 3: Implement minimal slice code**

Implement the smallest end-to-end slice that satisfies the specification.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add <slice-related-files>
git commit -m "feat: deliver first production-grade vertical slice"
```

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-10-anomaly-full-platform-design-blueprint.md`. Please review the plan. Does it capture what you want?

Which execution approach would you prefer?

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end.

**For this plan I recommend subagent-driven, because Tasks 1–3 are documentation-first and Task 4 is a security-sensitive code delivery that benefits from independent review.**

Does the plan capture what you want, and which approach should we use?
