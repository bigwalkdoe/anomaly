# Documentation Consistency and Production Checklist Design

## Intent

Reconcile the repository's operator- and developer-facing docs with the hardening work already shipped, and give release owners one canonical production-readiness gate backed by evidence rather than a loose list of reminders.

## Goals

- Provide a single `docs/PRODUCTION_READINESS.md` checklist that distinguishes release gates, operational verification, and known blockers.
- Link that checklist from `README.md`, `SECURITY.md`, and `docs/DEPLOYMENT_GUIDE.md` so it is discoverable from every normal entry point.
- Correct stale or incomplete facts in the existing docs: current Alembic head, Organization/Workspace status, deployment env vars, API idempotency/v1 behavior, WS auth, metrics protection, and upload limits.
- Add a lightweight docs consistency test so the canonical links and required checklist sections do not silently drift again.

## Non-goals

- Declaring the platform production-ready; the checklist remains a gate that must be satisfied with evidence.
- Implementing new security controls or changing runtime behavior.
- Rewriting historical `TASKS.md` progress entries; clarify the current baseline instead.
- Exhaustively documenting every planned platform capability from the blueprint.

## Constraints

- Documentation only, plus one pure docs test; no product code or migration changes.
- Current Alembic head is `b2c3d4e5f6a7`; historical head references in progress entries stay as history but the current baseline must be explicit.
- Python floor is 3.12+ per `pyproject.toml` and CI; do not change documented version floors.
- Preserve the honest pre-production posture in `README.md`.
- Checklist items must name concrete evidence commands or observable settings, not vague aspirations.

## Approaches

1. **Expand only `SECURITY.md`** — smallest diff, but leaves no canonical release artifact and does not fix deployment/API drift. Rejected.
2. **Standalone readiness checklist linked from existing docs, plus a consistency test** — creates one authoritative gate, keeps each guide focused, and prevents link/section drift. Chosen.
3. **Full rewrite of all guides and specs** — would maximize consistency but create large review noise and risk changing historical decisions. Rejected.

## Decisions

- The canonical checklist lives at `docs/PRODUCTION_READINESS.md`.
- `README.md`, `SECURITY.md`, and `docs/DEPLOYMENT_GUIDE.md` link to it; `SECURITY.md` keeps a short checklist summary pointing to the canonical file.
- The docs test lives at `tests/docs/test_documentation_consistency.py` and checks canonical links, required checklist sections, required control names, API idempotency documentation, and the explicit current Alembic head baseline.
- `TASKS.md` gains a current-baseline note near the top and a progress entry; historical progress lines are not rewritten beyond the last-updated date.
- Runtime verification remains the existing gates: `ruff check .`, `python3 -m mypy packages apps`, the full pytest suite, `alembic heads`, and `alembic check` where a migrated DB is available.

## Builder discretion

- Exact wording and table formatting of the guides are left to the implementer as long as the test assertions and constraints are satisfied.
- Checklist pass criteria may be expressed as commands, settings, or observable evidence; each gate must be checkable.
