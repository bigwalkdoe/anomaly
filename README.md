# Anomaly

Anomaly is an open-source, multi-user penetration-testing and cyber-operations platform in active development. The goal is to unify recon, vulnerability discovery, exploitation, post-exploitation, and defensive operations under one AI-orchestrated control plane with a shared data model, audit trail, and reporting pipeline.

> **Status:** Early-stage / pre-production. Core foundations are implemented and under validation, while major blueprint capabilities (full multi-tenancy, policy-gated execution, hardened isolated runners, complete evidence/report traceability, assets/incidents/workflows/billing) are still in progress. See [Current status](#current-status) and the [gap analysis](docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md).

## Current status

### Implemented foundations

- **Identity & access:** user auth, JWT/refresh flow, TOTP MFA with backup codes, account lockout, and role-based access control primitives (admin/pentester/client-viewer).
- **Engagement-centric workflow:** engagements, scope entries/targets, findings, runs, evidence, reports, tags, playbooks, schedules, notifications, audit logging, and WebSocket endpoints for run/notification updates.
- **Tooling layer:** tool wrappers/registry including nmap, nuclei, ffuf, sqlmap, httpx, recon/generic/stub components; worker execution path and runner interfaces exist (real hardened container execution remains incomplete).
- **AI layer (early):** provider-agnostic AI package with provider integrations and audited `suggest_tools` capability/API/CLI support.
- **Reporting:** Markdown/HTML/PDF report generation scaffolding (PDF output is currently a stub/placeholder in parts).
- **Interfaces:** FastAPI REST API with OpenAPI docs, Next.js 15 web UI, and Typer CLI command modules.
- **Operations & quality baseline:** Docker Compose dev/prod manifests, Helm chart skeleton, Prometheus metrics endpoint, structured logging groundwork, and a passing local Python test suite snapshot (**123 passed**, 2026-11-10).

### In progress / recently landed

- Alembic migration lineage consolidated to a canonical head with clean upgrade/check on validated environments.
- Lint/type-check parity improvements (Ruff clean; `mypy packages apps` clean in local validation).
- First production-grade vertical-slice work started (ADR/implementation-spec/gap-analysis docs added), including initial tenancy foundations and `organization_id` propagation across core entities and parts of the API.
- CLI hardening and broader test coverage improvements; runner image build validation and initial web smoke QA artifacts.

### Known gaps (not yet production-ready)

- **Tenancy & authorization depth:** full Organization/Workspace model and server-side tenant enforcement across all APIs/services/WS/exports/workers.
- **Governed execution:** approvals/policy decision service, policy-before-execution hooks, scope-validated isolated runner containment/limits, and complete job lifecycle.
- **Evidence & reporting integrity:** checksums/provenance/retention enforcement and end-to-end traceable, verifiable reports.
- **Platform breadth:** asset intelligence, incident/defensive workflows, full vulnerability lifecycle, workflow engine, AI sessions/metering/policy-gated actions, compliance mappings, billing/entitlements.
- **Security/ops hardening:** environment-specific browser/session hardening, dependency/security CI gates with approved remediation, staging/monitoring/backup-recovery automation, and comprehensive runtime QA.

For the authoritative baseline and ownership/status breakdown, see:

- [Full platform gap analysis](docs/superpowers/plans/2026-11-10-anomaly-full-platform-gap-analysis.md)
- [Full platform implementation spec](docs/superpowers/plans/2026-11-10-anomaly-full-platform-implementation-spec.md)
- [Full platform design blueprint](docs/superpowers/specs/2026-11-10-anomaly-full-platform-design-blueprint.md)
- [TASKS.md](TASKS.md)

## Quick start

### Docker Compose (development)

```bash
git clone https://github.com/bigwalkdoe/anomaly.git
cd anomaly
docker compose up -d
```

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

> Review `docker-compose.yml` / `docker-compose.prod.yml` and required secrets/env configuration before exposing any environment beyond local development.

### Local development

```bash
# Install packages/apps (editable)
pip install -e packages/core -e packages/tools -e packages/ai -e packages/reporting \
  -e packages/integrations -e packages/common -e apps/api -e apps/worker -e apps/cli

# Configure environment (example values)
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:5432/anomaly"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="change-me"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# Run database migrations
cd packages/core && alembic upgrade head

# Start API
cd ../../apps/api && uvicorn anomaly_api.main:app --reload

# Start worker (separate terminal)
cd ../worker && arq anomaly_worker.main:WorkerSettings
```

## Architecture

```text
anomaly/
├── apps/
│   ├── api/          # FastAPI REST + WebSocket control plane
│   ├── web/          # Next.js 15 web UI
│   ├── cli/          # Typer CLI
│   └── worker/       # ARQ background worker
├── packages/
│   ├── core/         # Models, DB/migrations, auth, RBAC, audit, scope, runner interfaces
│   ├── tools/        # Tool wrappers/adapters and registry
│   ├── ai/           # Provider-agnostic AI services
│   ├── reporting/    # Report generation
│   ├── integrations/ # External integrations (e.g. spectre)
│   └── common/       # Shared schemas/utilities
├── infra/            # Runner/container and infrastructure assets
├── deploy/           # Helm charts and deployment artifacts
├── tests/            # Cross-package/integration/security tests
└── docs/             # Guides, specs, plans, and design artifacts
```

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [API Guide](docs/API_GUIDE.md)
- [Security Guide](SECURITY.md)
- [Architecture / design spec](docs/superpowers/specs/2026-11-03-anomaly-design.md)
- [Task tracker](TASKS.md)

## Roadmap (high level)

Near-term priorities are driven by the full-platform blueprint and implementation spec:

1. **P0/P1 stabilization:** maintain migration/test/lint/type parity and close CI security/dependency gaps.
2. **First governed vertical slice:** end-to-end tenant-aware, policy-gated, scope-validated execution with approvals, evidence integrity/provenance, and traceable reporting.
3. **Tenancy & enforcement:** complete Organization/Workspace model and server-side enforcement across API, WebSocket, exports, and workers.
4. **Execution hardening:** real isolated runner containment, limits, and policy-before-execution controls.
5. **Platform expansion:** asset intelligence, incident/defensive workflows, workflow engine, richer AI governance, compliance outputs, and commercial/entitlement model.

## License

Apache 2.0
