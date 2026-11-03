# Anomaly — Design Document

**Date:** 2026-11-03
**Status:** Draft — pending approval
**Approach:** C (standalone product; spectre ecosystem as backends/data sources)
**License:** Apache 2.0

## 1. Intent and why

Anomaly is an open-source, multi-user penetration-testing and cyber-operations
platform. Today the user runs several disconnected tools and repos (spectre-agent,
spectre-suite, ad-hoc pentest scripts). Anomaly unifies them under one AI-
orchestrated roof: recon, vulnerability discovery and exploitation,
post-exploitation, and defensive operations (SOC triage, incident response,
detection engineering) in a single system with one data model, one audit trail,
and one reporting pipeline.

It must serve three distinct modes of use without forking the codebase:

- **Own infrastructure** — full ownership, aggressive exploitation and
  auto-remediation allowed; ties into spectre-suite monitoring.
- **Bug bounty** — strictly scope-bound, discovery-focused, no exploitation
  beyond proof-of-concept; bounty-style reporting.
- **Client engagements** — formal authorization, evidence handling, deliverable
  reports, per-client read-only access.

The "why now": the user already has the monitoring/security-data layer
(spectre-suite) and an agent runtime (spectre-agent). What's missing is a
product-shaped surface that turns that data plus pentest tooling into findings,
evidence, and reports, with multi-user access and AI orchestration.

## 2. Goals

- One engagement-centric data model shared by all three modes.
- AI orchestration of tool selection, chaining, and report/findings drafting.
- Containerized tool execution from day one, reproducible and isolated.
- Multi-user with roles and per-engagement access control, including client
  read-only portals.
- Browser UI for clients and triage; CLI for pentesters.
- Warn-and-log scope enforcement with a full audit trail (not hard blocks).
- Reuse spectre-agent's security summary and spectre-suite's scans as data
  sources rather than reimplementing them.
- Open source (Apache 2.0), self-hostable, documented.

## 3. Non-goals

- Replacing spectre-agent or spectre-suite. They remain the source of truth for
  host state and monitoring.
- Building a new vulnerability scanner from scratch. Anomaly orchestrates
  existing tools (nmap, nuclei, ffuf, sqlmap, metasploit, burp, etc.).
- Hard-blocking out-of-scope actions. Enforcement is warn-and-log.
- Multi-tenant SaaS hosting in v1. Self-hosted only; cloud-ready later.
- Automated exploitation against targets without an approved engagement and
  scope. (AI proposes; a human approves anything touching client scope.)

## 4. Anti-goals (what would make this a failure even if it technically works)

- A system that can be pointed at arbitrary targets with no engagement/scope
  record. Engagement-first is mandatory.
- Silent tool runs with no audit trail.
- AI that executes destructive commands without human approval on client scope.
- Duplicating spectre's monitoring stack instead of consuming it.

## 5. Constraints

- Multi-user from day one (no SQLite/single-user shortcut).
- Containerized tool runners from day one.
- Open source, Apache 2.0.
- Scope enforcement: warn and log.
- Self-hostable on a single machine initially (Fedora/Linux), cloud-ready later.
- Must integrate with existing spectre contracts:
  - `spectre-agent` `GET /api/security/summary` (published contract).
  - `spectre-suite` Prometheus metrics and Grafana stack.
- Port hygiene: avoid contested ports; document chosen ports.

## 6. Approaches considered

- **A — Standalone full product.** Rejected: duplicates monitoring/security data
  spectre already produces.
- **B — AI layer inside spectre-agent.** Rejected: multi-user browser portal and
  client access do not fit a single-user Fedora OS agent.
- **C — Standalone product, spectre as backends.** Chosen: real product surface
  and pentest-focused UX, reuses spectre data, no duplication.

## 7. Architecture overview

Monorepo with five deployable units plus shared packages:

```
anomaly/
├── apps/
│   ├── api/          # FastAPI REST + WebSocket (auth, engagements, findings, runs)
│   ├── web/          # Next.js 15 browser UI (triage, client portal, reports)
│   ├── cli/          # Typer CLI sharing schemas with api
│   ├── worker/       # arq worker: queues runs, streams logs, manages containers
│   └── runner/       # Container image(s) with pinned pentest toolsets
├── packages/
│   ├── core/         # Pydantic models, DB session, auth, RBAC, audit, scope checks
│   ├── tools/        # Tool wrappers (nmap, nuclei, ffuf, sqlmap, metasploit, ...)
│   ├── ai/           # Provider-agnostic LLM layer (Ollama/OpenAI/Anthropic)
│   └── reporting/    # Report templates (markdown/PDF/HTML)
├── infra/            # docker-compose, env templates, runner images
└── docs/
```

Data flow: Web/CLI → API (auth + RBAC + scope check) → Postgres (engagement,
finding, etc.) + Redis queue → Worker → spawns runner container → streams logs
via WebSocket → writes findings/evidence → AI drafts report → human approves →
report published to client portal.

External: API pulls spectre-agent security summary and spectre-suite Prometheus
metrics as read-only data sources for own-infra engagements.

## 8. Data model (core entities)

- **User** — id, email, name, password hash, roles (admin/pentester/client-viewer),
  status.
- **Role / Permission** — RBAC; permissions scoped per engagement.
- **Engagement** — id, name, mode (own-infra / bug-bounty / client), owner,
  client (nullable), status (draft/active/paused/closed), rules of engagement
  text, start/end dates.
- **Scope** — belongs to engagement; list of targets (domains/IPs/CIDRs/URLs),
  in-scope and out-of-scope entries, allowed tool categories, notes.
- **Target** — normalized asset within a scope (host, service, endpoint).
- **Run** — id, engagement, user, tool, target(s), status, queue position,
  container id, started/finished timestamps, parameters.
- **Finding** — id, engagement, target, title, severity, description, evidence
  refs, status (new/triaged/confirmed/fixed/false-positive), CVSS, reporter,
  AI-drafted flag, reviewer.
- **Evidence** — id, finding/run, type (screenshot, request/response, tool
  output, log), storage key (MinIO), metadata.
- **Report** — id, engagement, version, format, status (draft/review/published),
  content, published_at, author/approver.
- **AuditLog** — append-only; actor, action, resource, timestamp, metadata,
  engagement (nullable). Every tool invocation, scope check result (including
  warnings), AI call, and approval is recorded.

All timestamps UTC. Soft-delete on user-facing entities; audit log is immutable.

## 9. Auth and roles

- JWT access tokens (short-lived) + refresh tokens (rotating, stored hashed).
- Optional OAuth (Google/GitHub) for SSO; local password auth always available.
- RBAC: admin, pentester, client-viewer. Permissions are also gated per
  engagement (a pentester only sees engagements they're assigned to; a client
  only sees their own engagement's findings/reports).
- API keys for CLI/automation (scoped to a user, revocable), in addition to
  sessions.
- All endpoints require auth; `/api/health` and `/api/version` are unauthenticated
  (needed for monitoring/probes) but return no sensitive data.

## 10. Execution model

- Runs are queued in Redis (arq) and attributed to the requesting user.
- Worker spawns a Docker container from a pinned runner image per run, with:
  - target allowlist passed as env (scope enforcement happens in the API before
    enqueue; the runner also receives the allowlist for defense in depth).
  - resource limits (CPU/mem/timeout) per run.
  - read-only root filesystem where possible; writable scratch volume.
- Scope check (API layer): before enqueue, compare requested targets against the
  engagement scope. Out-of-scope → log a warning with full context and proceed
  (warn-and-log), but mark the run `scope_warning=true` and surface it in the UI.
- Live logs streamed from container stdout/stderr over WebSocket to the UI and
  stored as evidence.
- Tool wrappers in `packages/tools` translate between Anomaly's run parameters
  and each tool's CLI flags; each wrapper declares its supported target types
  and required scope categories.
- Evidence (screenshots, HTTP transcripts, tool output) uploaded to MinIO with
  metadata in Postgres.

## 11. AI layer

- Provider-agnostic interface: Ollama (default, local, free), OpenAI, Anthropic.
  Configured per deployment via env; per-engagement override allowed.
- Capabilities:
  - Tool selection and chaining suggestions (human approves before execution on
    client scope).
  - Finding drafting from run output (title, severity, description, remediation).
  - Report drafting (executive summary, technical details, remediation plan).
  - Triage assistance (dedup, severity normalization, false-positive hints).
- Every prompt, response, and tool invocation is written to the audit log with
  model name, token counts, and the resulting action.
- AI never executes destructive commands without explicit human approval on
  client scope; on own-infra, auto-remediation is allowed but logged.

## 12. CLI

- Python Typer, sharing Pydantic models/schemas with the API (monorepo
  `packages/core`).
- Commands: auth (login), engagements (list/create/scope), runs (start/status/
  logs), findings (list/create/update), reports (generate/publish), sync (pull
  spectre data), config, version.
- Outputs: human-readable tables + `--json` for scripting, consistent with
  spectre-agent CLI conventions.

## 13. Web UI

- Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui.
- Areas: Dashboard (engagement overview, recent runs/findings), Engagements
  (create, scope editor, targets), Runs (queue, live logs, results), Findings
  (triage, severity, evidence), Reports (draft/review/publish), Client portal
  (read-only findings + published reports for client-viewer role), Admin (users,
  roles, audit log viewer, tool image management).
- Real-time run logs via WebSocket.

## 14. Integration with spectre ecosystem

- **spectre-agent**: consume `GET /api/security/summary` for own-infra
  engagements to import unresolved findings as Anomaly findings (linked, not
  duplicated). Read-only.
- **spectre-suite**: consume Prometheus metrics and reuse its Grafana stack for
  Anomaly's own observability; optionally surface Anomaly metrics
  (`anomaly_runs_total`, `anomaly_findings_by_severity`, etc.) into the same
  Grafana.
- Anomaly does not modify spectre data; integration is pull-only and
  documented as a versioned contract.

## 15. Standardization proposal (spectre ecosystem)

Anomaly should be the first project to adopt a shared standard, so the rest of
the ecosystem can converge on it over time. Proposed shared package
`spectre-common` (Python), consumed by Anomaly from day one and by
spectre-agent incrementally:

- Pydantic settings base + 4-level config hierarchy (reuse spectre-agent's
  model).
- Structured logging + Prometheus metrics helpers with standard labels.
- Auth primitives: JWT + RBAC + API keys.
- DB session factory (SQLAlchemy async) + Alembic migration helpers.
- Standard health/version endpoints and error envelope.
- Standard docker-compose + env-var conventions and port registry.

Conventions to standardize across all projects:
- API: OpenAPI, standard error envelope `{error, code, details}`, cursor
  pagination, `Authorization: Bearer` for new projects (spectre-agent keeps
  `X-API-Key` for compat).
- Observability: common metric prefix convention, health check shape, Grafana
  dashboard templates.
- Deployment: standard `.env.example`, port registry document, compose layout.
- Integration contracts: versioned, documented (like security/summary).
- Tooling: shared ruff/mypy/pytest config, reusable GitHub Actions workflows.

**Scope note:** Building `spectre-common` and migrating spectre-agent is a
separate effort that Anomaly's conventions will feed. For v1, Anomaly will
implement these conventions internally (`packages/core`) in a way that can be
extracted into `spectre-common` later without rework. Whether to start
`spectre-common` as its own repo now or extract later is an open decision
(see §17).

## 16. What's left to the builder

- Exact DB schema and indexes (follow the entity list in §8).
- Tool wrapper implementations and the runner image build (Dockerfile).
- Report template formats and PDF rendering library.
- Migration strategy from spectre-agent's auth model (X-API-Key) to JWT.
- Test strategy (unit/integration/e2e) and CI pipeline details.
- Specific port assignments and runner resource limits.
- Whether `spectre-common` is created now or extracted later.

## 16a. Builder's calls (settled during builder check)

These are decisions a sensible builder can make without changing what gets
built. Recorded here so the user can override while reading.

- **Cross-engagement data isolation:** enforced in the repository/query layer
  (application-level filtering by engagement + user permissions), with
  integration tests asserting no cross-engagement data leakage. RLS is not used
  in v1 to keep migrations and testing simple; revisit if multi-tenant SaaS is
  added.
- **Tool output contract:** every tool wrapper must support a structured
  output mode (JSON or XML) and parse results into a common `ToolResult`
  schema (stdout, stderr, exit code, parsed findings, artifacts). Raw text is
  retained as evidence but never parsed heuristically as the primary path.
- **Finding deduplication:** fingerprint = (engagement, target, tool/template,
  normalized title). New runs attach to an existing finding when the fingerprint
  matches; otherwise create a new finding.
- **Report publishing:** publishing creates an immutable snapshot (version
  bump, content frozen). Unpublishing is not supported in v1; corrections
  produce a new version.
- **Evidence retention default:** retain evidence for closed engagements for
  90 days by default, configurable via env; purged by a scheduled worker job.
  (Subject to override per the open question below.)

## 17. Decisions (reliable defaults, overridable)

Made per reliable design practice: smallest scope that ships, explicit audit
records, reuse existing tooling, defer coupling until contracts stabilize.

1. **spectre-agent integration data shape** — spectre-agent gains a read-only
   incidents/findings endpoint (extending the published-contract pattern of
   `/api/security/summary`). Anomaly imports them as linked findings. Until that
   endpoint exists, the integration is disabled and Anomaly runs its own scans.
   (Cross-repo change tracked as a separate task; not blocking v1 core.)
2. **Approval model** — separate `Approval` record (auditable, supports
   multi-step review). Required for destructive actions on client scope and for
   any auto-remediation; on own-infra a pentester may self-approve but the
   approval record is still written.
3. **Auto-remediation in v1** — integrate spectre-suite's `ml_fix_engine`
   (reuse its allow/deny-list and approval-file model); Anomaly does not build
   a second remediation engine. v1 supports report + dry-run + manual apply.
4. **Workflow/Playbook entity** — include a `Playbook` entity (ordered steps:
   tool, params, condition, on_failure). AI can generate; users can save and
   reuse. Chaining is first-class, not implicit.
5. **Target auto-creation** — recon tools auto-create `Target` records tagged
   `discovered` (candidates). They are not in-scope for active scanning until a
   pentester confirms them. Safety over convenience.
6. **SOC alerting in v1** — webhook alerting on new critical/high findings
   (integrates with spectre-suite's Alertmanager). Email optional, deferred.
7. **spectre-common timing** — implement conventions in `packages/core` now;
   extract to a `spectre-common` repo later once stable. No new repo in v1.
8. **Runner image strategy** — one fat image for v1 (simpler, fewer moving
   parts); build structured so per-category split is mechanical later.
9. **Client portal hosting** — same deployment with RBAC. One deployment, one
   ops story.
10. **Evidence retention** — 90 days default for closed engagements,
    configurable via env; purged by scheduled worker job.

## 18. Approval

Pending. Once approved, next step is `superpowers:writing-plans`.