# Anomaly

Anomaly is an open-source, multi-user penetration-testing and cyber-operations platform in active development. It aims to unify recon, vulnerability discovery, exploitation, post-exploitation, and defensive operations under one AI-orchestrated control plane with a shared data model, audit trail, and reporting pipeline.

> **Status:** Early-stage / pre-production. Core foundations are implemented and under active hardening, while major blueprint capabilities (full multi-tenancy/workspace enforcement, complete policy-gated execution, hardened isolated runners, end-to-end evidence/report traceability, assets/incidents/workflows/billing, and broader platform breadth) remain in progress. CI is currently green on `main`, but the platform is **not production-ready**.

## Current status

### Implemented foundations

- **Identity & access:** user auth, JWT access/refresh flow, TOTP MFA with backup codes, login lockout controls, and role-based access primitives (`admin`, `pentester`, `client_viewer`).
- **Engagement-centric workflow:** engagements, scope entries/targets, findings, runs, evidence, reports, tags, playbooks, schedules, notifications, audit logging, and WebSocket endpoints for run/notification updates.
- **API surface:** FastAPI REST API with OpenAPI docs (`/docs`, `/redoc`), legacy `/api/*` endpoints, and an additive `/api/v1/*` slice for key auth/engagement/run/report flows (envelope responses on v1 routes).
- **Tooling layer:** tool wrappers/registry and parsers (nmap, nuclei, ffuf, sqlmap, httpx, recon/stub components), worker execution path, and runner interfaces (fully hardened containerized execution/isolation is still incomplete).
- **AI layer (early):** provider-agnostic AI package with provider integrations and audited `suggest_tools` capability exposed via API/CLI.
- **Reporting:** Markdown/HTML/PDF report generation scaffolding and persisted report artifacts/traceability metadata in supported flows (PDF output remains limited/stubbed in parts).
- **Interfaces:** Next.js web UI and Typer-based CLI modules for core workflows.
- **Operations & quality baseline:** Docker Compose manifests, Helm chart skeleton, metrics endpoint, structured logging groundwork, Alembic migration lineage, lint/typecheck/test suites, and CI jobs (lint, typecheck, tests, docker build, Bandit, dependency scan, web checks, gitleaks).

### Recent progress

- **Tenant/enforcement hardening:** improved engagement-scoped access semantics (including no-leak behavior where applicable), tightened RBAC on sensitive surfaces (schedules, uploads, findings mutations, run detail/status reads, report generation/access), and expanded cross-tenant/RBAC test coverage.
- **Governed execution groundwork:** centralized assessment policy/enqueue helpers, shared manifest/audit flow for run creation paths (including playbook step enqueue batching with preserved inline behavior), and continued alignment of API routes to policy-gated execution patterns.
- **CLI and API hardening:** defensive request/response handling, timeout/error improvements, contract-aligned command behavior, and additive endpoint compatibility fixes (e.g. v1 report generation contract alignment).
- **CI/security wiring:** workflow validation/fixes, Bandit and project-scoped dependency scanning integration, and gitleaks coverage in CI.

### Known gaps (not yet production-ready)

- **Tenancy & authorization depth:** complete Organization/Workspace model and consistent server-side tenant enforcement across all APIs/services/WebSockets/exports/workers.
- **Governed execution:** full approvals/policy decision service, policy-before-execution hooks across all execution entry points, scope-validated isolated runner containment/limits, and complete job lifecycle controls.
- **Evidence & reporting integrity:** comprehensive checksums/provenance/retention enforcement and fully traceable, verifiable reports end-to-end.
- **Platform breadth:** asset intelligence, incident/defensive workflows, full vulnerability lifecycle, workflow engine, AI sessions/metering/policy-gated actions, compliance mappings, and billing/entitlements.
- **Security/ops hardening:** production-grade session/browser hardening, dependency/security remediation SLAs, staging/monitoring/backup-recovery automation, and comprehensive authenticated runtime QA.

For authoritative planning/status details, see:

- [Full platform gap analysis](docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md)
- [Full platform implementation spec](docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md)
- [Full platform design blueprint](docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md)
- [TASKS.md](TASKS.md)

## Quick start

### Prerequisites

- Docker / Docker Compose
- Python 3.12+
- Node.js 22+ (for web UI development/build)

### 1) Start infrastructure dependencies (development)

The default `docker-compose.yml` starts local infrastructure services (Postgres, Redis, MinIO) with ports mapped to the `2010x` dev block:

```bash
git clone https://github.com/bigwalkdoe/anomaly.git
cd anomaly
cp .env.example .env  # adjust as needed
docker compose up -d
```

Default local endpoints (from compose/env defaults):

- Postgres: `localhost:20102`
- Redis: `localhost:20103`
- MinIO API: `localhost:20104` (console: `localhost:20105`)

### 2) Run API, worker, and web locally

```bash
# Install Python packages/apps (editable)
pip install -e packages/core -e packages/tools -e packages/ai -e packages/reporting \
  -e packages/integrations -e packages/common -e apps/api -e apps/worker -e apps/cli

# Configure environment (example values; match docker-compose.yml / .env.example)
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:20102/anomaly"
export REDIS_URL="redis://localhost:20103/0"
export JWT_SECRET="change-me"
export MINIO_ENDPOINT="localhost:20104"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# Run database migrations
cd packages/core && alembic upgrade head

# Start API (new terminal/session as needed)
cd ../../apps/api && uvicorn anomaly_api.main:app --reload --port 20101

# Start worker (new terminal/session)
cd ../worker && arq anomaly_worker.main:WorkerSettings

# Start web UI (new terminal/session)
cd ../web && npm ci && npm run dev -- --port 20100
```

- Web UI: http://localhost:20100
- API docs: http://localhost:20101/docs

> Ports and origins may vary by environment/configuration. Review `.env.example`, `docker-compose.yml`, and `docker-compose.prod.yml` before exposing any environment beyond local development.

### Production-style compose (WIP)

`docker-compose.prod.yml` provides a fuller multi-service stack (including API/web/worker/runner images and required secrets). Treat it as evolving infrastructure and review security, networking, secrets, and hardening requirements before use.

## Architecture

```text
anomaly/
├── apps/
│   ├── api/          # FastAPI REST + WebSocket control plane
│   ├── web/          # Next.js web UI
│   ├── cli/          # Typer CLI
│   └── worker/       # ARQ background worker / execution orchestration
├── packages/
│   ├── core/         # Models, DB/migrations, auth, RBAC, audit, scope, policy/execution helpers
│   ├── tools/        # Tool wrappers/adapters, parsers, and registry
│   ├── ai/           # Provider-agnostic AI services
│   ├── reporting/    # Report generation and templates
│   ├── integrations/ # External integrations (e.g. spectre)
│   └── common/       # Shared schemas/utilities
├── infra/            # Runner/container and infrastructure assets
├── deploy/           # Helm charts and deployment artifacts
├── tests/            # API/core/tools/reporting/CLI/integration tests
└── docs/             # Guides, specs, plans, and design artifacts
```

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [API Guide](docs/API_GUIDE.md)
- [Security Guide](SECURITY.md)
- [Task tracker](TASKS.md)
- [Design/specs and plans](docs/superpowers/)

## Development

```bash
# Lint
ruff check .

# Type check
mypy packages apps

# Tests (example targeted subset; configure DB/services as needed)
python3 -m pytest -q tests/api tests/core tests/tools tests/reporting
```

CI workflows run linting, type checking, tests, image/build checks, and security/dependency scans on pushes and pull requests.

## Roadmap (high level)

Near-term priorities are driven by the full-platform blueprint and implementation spec:

1. **Stabilization:** maintain migration/test/lint/type parity and keep CI/security gates actionable.
2. **First governed vertical slice:** complete tenant-aware, policy-gated, scope-validated execution with approvals, evidence integrity/provenance, and traceable reporting.
3. **Tenancy & enforcement:** finalize Organization/Workspace model and server-side enforcement across API, WebSocket, exports, and workers.
4. **Execution hardening:** real isolated runner containment, limits, and policy-before-execution controls.
5. **Platform expansion:** asset intelligence, incident/defensive workflows, workflow engine, richer AI governance, compliance outputs, and commercial/entitlement model.

## License

Apache 2.0
