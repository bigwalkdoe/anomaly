# Anomaly

Anomaly is an open-source, multi-user penetration-testing and cyber-operations platform. It unifies recon, vulnerability discovery, exploitation, post-exploitation, and defensive operations under one AI-orchestrated roof with one data model, one audit trail, and one reporting pipeline.

## Features

- **Multi-user with RBAC**: Admin, pentester, and client-viewer roles with per-engagement access control
- **Engagement-first**: All activity is tied to engagements with scope enforcement (warn-and-log)
- **Containerized tool execution**: Docker-based tool runners (nmap, nuclei, ffuf, sqlmap, httpx, etc.)
- **AI orchestration**: Provider-agnostic LLM layer (Ollama, OpenAI, Anthropic) for finding/report drafting
- **Multi-factor authentication**: TOTP-based MFA with backup codes
- **Account lockout**: Automatic lockout after repeated failed login attempts
- **Real-time notifications**: WebSocket-based notifications and run log streaming
- **Playbook engine**: Multi-step tool execution workflows
- **Scheduled runs**: Cron-based automated scanning
- **File upload**: MinIO evidence store integration
- **Report generation**: Markdown, HTML, and PDF report templates
- **Audit logging**: Immutable audit trail for all state-changing actions
- **Prometheus metrics**: `/api/metrics` endpoint for monitoring
- **REST API**: Comprehensive REST API with OpenAPI docs
- **Web UI**: Next.js browser UI for triage and client portals
- **CLI**: Python Typer CLI for pentesters

## Quick Start

### Docker Compose

```bash
git clone https://github.com/bigwalkdoe/anomaly.git
cd anomaly
docker compose up -d
```

Access the web UI at http://localhost:3000
Access the API docs at http://localhost:8000/docs

### Development

```bash
# Install dependencies
pip install -e packages/core -e packages/tools -e packages/ai -e packages/reporting -e packages/integrations -e packages/common -e apps/api -e apps/worker -e apps/cli

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:5432/anomaly"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="***REMOVED***"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# Run database migrations
cd packages/core && alembic upgrade head

# Start API
cd ../apps/api && uvicorn anomaly_api.main:app --reload

# Start worker
cd ../apps/worker && arq anomaly_worker.main:WorkerSettings
```

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Getting started guide
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [API Guide](docs/API_GUIDE.md) - Complete API reference
- [Security Guide](SECURITY.md) - Security hardening
- [Design Spec](docs/superpowers/specs/2026-11-03-anomaly-design.md) - Architecture spec

## Architecture

```
anomaly/
├── apps/
│   ├── api/          # FastAPI REST + WebSocket
│   ├── web/          # Next.js 15 browser UI
│   ├── cli/          # Typer CLI
│   ├── worker/       # arq worker
│   └── runner/       # Container images
├── packages/
│   ├── core/         # Models, DB, auth, RBAC, audit, scope
│   ├── tools/        # Tool wrappers (nmap, nuclei, ffuf, ...)
│   ├── ai/           # Provider-agnostic LLM layer
│   ├── reporting/    # Report templates
│   ├── integrations/ # spectre-agent, spectre-suite
│   └── common/       # Shared schemas and utilities
├── infra/            # Docker, Helm charts
└── docs/             # Documentation
```

## Roadmap

- Real tool packs with containerized execution
- AI-powered finding and report drafting
- CLI and web UI for pentesters and clients
- Reporting with PDF generation
- Integrations with spectre-agent and spectre-suite
- Standardization extraction (spectre-common)

## License

Apache 2.0
