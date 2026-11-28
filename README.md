# Anomaly

[![CI](https://github.com/bigwalkdoe/anomaly/actions/workflows/ci.yml/badge.svg)](https://github.com/bigwalkdoe/anomaly/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](pyproject.toml)
[![Node](https://img.shields.io/badge/node-22%2B-339933.svg)](apps/web/package.json)

**Anomaly is an open-source control plane for governed security operations.**  
It brings engagements, scope, policy-aware execution, evidence, audit trails, and reporting into one multi-user platform—built for teams that need more than a collection of scanner wrappers.

> **Pre-production / active development.**  
> Anomaly has real foundations and active hardening, but it is **not production-ready**. Full tenancy enforcement, complete governed execution across every entry point, hardened isolated runners, and end-to-end evidence/report integrity are still in progress.

## Why Anomaly

Most security tooling stops at “run a tool, get output.” Anomaly is being built around the operational controls that make security work defensible:

- **Scope-aware execution** — targets are evaluated against engagement scope before runs are enqueued.
- **Policy before execution** — shared policy/manifest/enqueue flow, with worker-side re-validation before execution.
- **Audit by default** — sensitive actions emit audit events, including execution, evidence, report, and schedule flows.
- **Evidence and traceability** — runs, evidence, and reports carry provenance/traceability metadata in supported flows.
- **Multi-user control plane** — RBAC primitives, engagement membership semantics, and tenant/no-leak hardening are actively being enforced.

## Governed execution flow

```mermaid
flowchart LR
    A[Engagement & Scope] --> B[Policy / Approval Checks]
    B --> C[Execution Manifest + Enqueue]
    C --> D[Worker Re-validation]
    D --> E[Runner Execution]
    E --> F[Evidence + Audit Trail]
    F --> G[Findings / Reports / Traceability]
```

The goal is simple: every assessment action should be attributable, scoped, policy-checked, and traceable.

## What’s in the box

| Area | Current state |
|---|---|
| **Identity & access** | User auth, JWT access/refresh, TOTP MFA + backup codes, login lockout controls, RBAC primitives (`admin`, `pentester`, `client_viewer`) |
| **Engagement workflow** | Engagements, scope/targets, findings, runs, evidence, reports, tags, playbooks, schedules, notifications, audit logs, WebSocket updates |
| **Governed execution** | Shared policy/enqueue/manifest helpers, scheduler dispatch through core policy flow, worker pre-execution re-validation, schedule dispatch visibility metadata |
| **Runner layer** | Tool wrappers/registry/parsers, DockerRunner execution/timeout/cleanup, default `network="none"`, output/artifact guardrails; full containment hardening still ongoing |
| **Evidence & reporting** | SHA/provenance metadata, evidence integrity/audit endpoints, report traceability in supported flows, retention foundations; object-store verification/retention wiring still evolving |
| **API & interfaces** | FastAPI REST + OpenAPI (`/docs`, `/redoc`), legacy `/api/*`, additive `/api/v1/*` slice, Next.js web UI, Typer CLI |
| **AI (early)** | Provider-agnostic AI package with audited `suggest_tools` capability exposed via API/CLI |
| **Ops baseline** | Docker Compose, Helm skeleton, metrics, structured logging groundwork, Alembic migrations, lint/typecheck/tests, CI/security scans |

## Known gaps

Anomaly is intentionally honest about what is not done yet:

- **Tenancy depth** — complete Organization/Workspace model and consistent server-side enforcement across APIs, WebSockets, exports, and workers.
- **Complete governed execution** — approvals/policy decision coverage across every execution entry point, full job lifecycle controls, and hardened isolated runner containment/limits.
- **Evidence/report integrity** — comprehensive object-store checksum verification, retention enforcement wiring, and fully verifiable end-to-end traceability.
- **Platform breadth** — asset intelligence, incident/defensive workflows, full vulnerability lifecycle, workflow engine, AI sessions/metering/policy-gated actions, compliance mappings, billing/entitlements.
- **Production hardening** — session/browser hardening, dependency/security remediation SLAs, staging/monitoring/backup-recovery automation, authenticated runtime QA.

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) / Docker Compose
- [Python 3.12+](https://www.python.org/)
- [Node.js 22+](https://nodejs.org/) (for the web UI)

### 1. Start local infrastructure

The default `docker-compose.yml` starts Postgres, Redis, and MinIO on the local `2010x` dev port block.

```bash
git clone https://github.com/bigwalkdoe/anomaly.git
cd anomaly
cp .env.example .env
docker compose up -d
```

| Service | Endpoint |
|---|---|
| Postgres | `localhost:20102` |
| Redis | `localhost:20103` |
| MinIO API | `localhost:20104` |
| MinIO Console | `localhost:20105` |

### 2. Run the platform locally

```bash
# Install Python packages/apps (editable)
pip install -e packages/core -e packages/tools -e packages/ai -e packages/reporting \
  -e packages/integrations -e packages/common -e apps/api -e apps/worker -e apps/cli

# Environment (match .env.example / docker-compose.yml)
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:20102/anomaly"
export REDIS_URL="redis://localhost:20103/0"
export JWT_SECRET="change-me"
export MINIO_ENDPOINT="localhost:20104"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# Run migrations
cd packages/core && alembic upgrade head

# API (new terminal)
cd ../../apps/api && uvicorn anomaly_api.main:app --reload --port 20101

# Worker (new terminal)
cd ../worker && arq anomaly_worker.main:WorkerSettings

# Web UI (new terminal)
cd ../web && npm ci && npm run dev -- --port 20100
```

Local URLs:

- Web UI: http://localhost:20100
- API docs: http://localhost:20101/docs

> Review `.env.example`, `docker-compose.yml`, and `docker-compose.prod.yml` before exposing any environment beyond local development.

### Production-style compose

`docker-compose.prod.yml` provides a fuller multi-service stack (API/web/worker/runner images, required secrets). Treat it as evolving infrastructure—review security, networking, secrets, and hardening before use.

## Architecture

```text
anomaly/
├── apps/
│   ├── api/          # FastAPI REST + WebSocket control plane
│   ├── web/          # Next.js web UI
│   ├── cli/          # Typer CLI
│   └── worker/       # ARQ worker / execution orchestration
├── packages/
│   ├── core/         # Models, migrations, auth, RBAC, audit, scope, policy/execution helpers
│   ├── tools/        # Tool wrappers/adapters, parsers, registry
│   ├── ai/           # Provider-agnostic AI services
│   ├── reporting/    # Report generation and templates
│   ├── integrations/ # External integrations
│   └── common/       # Shared schemas/utilities
├── infra/            # Runner/container and infrastructure assets
├── deploy/           # Helm charts and deployment artifacts
├── tests/            # API, core, tools, reporting, CLI, integration tests
└── docs/             # Guides, specs, plans, design artifacts
```

## Development

```bash
# Lint
ruff check .

# Type check
mypy packages apps

# Tests (configure DB/services as needed; targeted example)
python3 -m pytest -q tests/api tests/core tests/tools tests/reporting
```

CI runs lint, typecheck, tests, Docker/build checks, web checks, Bandit, dependency scan, and gitleaks on pushes and pull requests.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [API Guide](docs/API_GUIDE.md)
- [Security Policy](SECURITY.md)
- [Production Readiness Checklist](docs/PRODUCTION_READINESS.md)
- [Task Tracker](TASKS.md)
- [Specs & Plans](docs/superpowers/)

Planning references:

- [Full platform gap analysis](docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md)
- [Full platform implementation spec](docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md)
- [Full platform design blueprint](docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md)

## Security

See [SECURITY.md](SECURITY.md) for the security policy and reporting process. If you discover a vulnerability, follow the private disclosure process documented there—do not open a public issue for sensitive security reports.

## Roadmap

1. **Stabilization** — keep migration, lint/type/test parity green; keep CI/security gates actionable.
2. **Governed vertical slice** — tenant-aware, policy-gated, scope-validated execution with approvals, evidence integrity/provenance, and traceable reporting.
3. **Tenancy & enforcement** — complete Organization/Workspace model and server-side enforcement across API, WebSocket, exports, and workers.
4. **Execution hardening** — real isolated runner containment, limits, and policy-before-execution controls.
5. **Platform expansion** — asset intelligence, defensive workflows, workflow engine, richer AI governance, compliance outputs, and commercial/entitlement model.

## License

[Apache 2.0](LICENSE)
