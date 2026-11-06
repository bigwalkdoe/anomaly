# Anomaly Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the anomaly monorepo with a working, tested API (auth, RBAC, engagements, findings, scope enforcement, audit log) and a containerized run pipeline proven end-to-end by a stub tool, so every later feature (real tools, AI, CLI, web, reporting) builds on a solid, tested base.

**Architecture:** Monorepo with `packages/core` (models, DB, auth, RBAC, audit, scope) shared by `apps/api` (FastAPI) and `apps/worker` (arq). Postgres + Redis + MinIO via docker-compose. A `RunnerBackend` protocol abstracts container execution so tests use a fake. Each task ends in a green test suite and a commit.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async + Alembic, Postgres 16, Redis 7, arq, Pydantic v2, PyJWT, passlib[bcrypt], pytest + pytest-asyncio + httpx, ruff, mypy, Docker.

**Spec:** `docs/superpowers/specs/2026-11-03-anomaly-design.md`

## Plan series (one plan per subsystem; this is plan 1)

1. **Foundation (this plan)** — monorepo, core, auth, RBAC, engagements/findings, scope, audit, run pipeline + stub tool.
2. Real tool packs (nmap, nuclei, ffuf, sqlmap, metasploit, burp, recon).
3. AI layer (provider-agnostic LLM, finding/report drafting, tool suggestion).
4. CLI (Typer, shared schemas).
5. Web UI (Next.js triage + client portal).
6. Reporting (templates, PDF, publishing, immutable snapshots).
7. Integrations (spectre-agent findings endpoint, spectre-suite metrics).
8. Standardization extraction (`spectre-common`).

Each plan produces working, testable software on its own.

## Global Constraints

- Python 3.12+; FastAPI; SQLAlchemy 2.0 async; Alembic; Postgres 16; Redis 7.
- All timestamps UTC (timezone-aware).
- Every endpoint except `/api/health` and `/api/version` requires auth.
- Audit log is append-only and immutable.
- Scope check runs before enqueue; out-of-scope → warn + log + mark `scope_warning=true`.
- Containerized execution is the default; `FakeRunner` is test-only.
- Ruff + mypy clean on changed files; pytest green before commit.
- Apache 2.0 license header not required in files; LICENSE file at root.

## Review Focus

1. Cross-engagement data leakage: a pentester or client-viewer must never read another engagement's findings; tests must assert 403/404, not just 200-with-empty.
2. Auth boundary: refresh-token rotation and revocation; a stolen refresh token must not grant indefinite access.
3. Scope enforcement: out-of-scope targets must still be logged with full context (target, user, engagement) before the run is enqueued; missing context is a silent failure.
4. Audit completeness: every state-changing action (create/update/delete, run enqueue, scope warning, approval) must produce an audit row; tests should count rows.
5. Container escape / host access: runner containers must not have host network or privileged mode by default; a misconfigured runner is a security regression.

---

## File Structure (foundation)

```
anomaly/
├── LICENSE
├── README.md
├── pyproject.toml                      # root project + workspace deps
├── .env.example
├── .gitignore
├── docker-compose.yml                  # postgres, redis, minio
├── Makefile
├── packages/
│   └── core/
│       ├── pyproject.toml
│       └── src/anomaly_core/
│           ├── __init__.py
│           ├── config.py                # settings (pydantic-settings)
│           ├── db.py                   # async engine + session factory
│           ├── models/                  # one file per entity group
│           │   ├── __init__.py
│           │   ├── user.py
│           │   ├── engagement.py
│           │   ├── finding.py
│           │   ├── run.py
│           │   ├── audit.py
│           │   └── approval.py
│           ├── auth.py                  # hashing, JWT issue/verify
│           ├── rbac.py                  # roles, permissions, access checks
│           ├── scope.py                 # scope check + warning
│           ├── audit.py                 # audit service
│           └── runner.py                # RunnerBackend protocol + impls
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   └── src/anomaly_api/
│   │       ├── main.py
│   │       ├── deps.py                 # current user, db session
│   │       ├── middleware.py
│   │       └── routers/
│   │           ├── health.py
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── engagements.py
│   │           ├── findings.py
│   │           ├── runs.py
│   │           └── audit.py
│   └── worker/
│       ├── pyproject.toml
│       └── src/anomaly_worker/
│           ├── main.py                  # arq worker entry
│           ├── executor.py              # run execution orchestration
│           └── tasks.py                # arq task defs
├── infra/
│   └── runner/
│       └── Dockerfile                  # fat tool image (stub for now)
├── tests/
│   ├── conftest.py
│   ├── core/
│   └── api/
└── .github/workflows/ci.yml
```

---

### Task 1: Repository scaffolding + tooling + container services

**Files:**
- Create: `LICENSE`, `README.md`, `.gitignore`, `.env.example`, `pyproject.toml`, `docker-compose.yml`, `Makefile`, `packages/core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `.github/workflows/ci.yml` (CI in Task 9)

**Interfaces:** none yet (foundation).

- [ ] **Step 1: Create root directory layout and license**

Create directories: `packages/core/src/anomaly_core`, `packages/core/tests`, `apps/api/src/anomaly_api/routers`, `apps/worker/src/anomaly_worker`, `tests/core`, `tests/api`, `infra/runner`, `docs`.

Write `LICENSE` (Apache 2.0 full text). Write `README.md` (project name, one-paragraph description, quick start placeholder).

- [ ] **Step 2: Write `.gitignore` and `.env.example`**

`.gitignore`: Python caches, venv, `.env`, `*.db`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `node_modules`, dist.

`.env.example` with exact keys:
```
DATABASE_URL=postgresql+asyncpg://anomaly:anomaly@localhost:5432/anomaly
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-in-production
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=7
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=anomaly-evidence
RUNNER_IMAGE=anomaly-runner:dev
RUNNER_NETWORK=anomaly-net
```

- [ ] **Step 3: Write root `pyproject.toml`**

```toml
[project]
name = "anomaly"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = ["packages/core", "apps/api", "apps/worker"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests", "packages", "apps"]
```

- [ ] **Step 4: Write package `pyproject.toml` files**

`packages/core/pyproject.toml`:
```toml
[project]
name = "anomaly-core"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "sqlalchemy[asyncio]>=2.0.30",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "pyjwt>=2.8",
  "passlib[bcrypt]>=1.7.4",
  "redis>=5.0",
  "arq>=0.26",
  "httpx>=0.27",
  "minio>=7.2",
]
```

`apps/api/pyproject.toml`:
```toml
[project]
name = "anomaly-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["anomaly-core", "fastapi>=0.111", "uvicorn[standard]>=0.30", "python-multipart>=0.0.9"]
```

`apps/worker/pyproject.toml`:
```toml
[project]
name = "anomaly-worker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["anomaly-core", "arq>=0.26", "docker>=7.1"]
```

- [ ] **Step 5: Write `docker-compose.yml`**

Services: `postgres` (image postgres:16, env POSTGRES_USER/PASSWORD/DB = anomaly, port 5432, volume), `redis` (redis:7, port 6379), `minio` (minio/minio, ports 9000/9001, env MINIO_ROOT_USER/PASSWORD). All on a named network `anomaly-net`. Healthchecks on postgres and redis.

- [ ] **Step 6: Write `Makefile`**

Targets: `up` (docker compose up -d), `down`, `test` (pytest), `lint` (ruff check .), `typecheck` (mypy packages apps), `migrate` (alembic upgrade head).

- [ ] **Step 7: Verify scaffolding**

Run: `docker compose up -d && docker compose ps`
Expected: postgres, redis, minio all healthy.

Run: `python -c "import anomaly_core"` (after `pip install -e packages/core`)
Expected: no error.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "chore: scaffold anomaly monorepo"
```

---

### Task 2: Core config, database, and Alembic

**Files:**
- Create: `packages/core/src/anomaly_core/config.py`, `db.py`, `packages/core/alembic.ini`, `packages/core/alembic/env.py`, `packages/core/alembic/versions/0001_base.py` (generated)
- Test: `tests/core/test_db.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings, loads from env), `get_settings()`, `engine` (AsyncEngine), `SessionLocal` (async sessionmaker), `Base` (DeclarativeBase), `get_db()` async generator (FastAPI dependency).

- [ ] **Step 1: Write failing test `tests/core/test_db.py`**

```python
import pytest
from anomaly_core.db import Base, engine


@pytest.mark.asyncio
async def test_engine_connects():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    assert engine is not None
```

- [ ] **Step 2: Run test — expect FAIL (modules missing)**

Run: `pytest tests/core/test_db.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "anomaly-evidence"
    runner_image: str = "anomaly-runner:dev"
    runner_network: str = "anomaly-net"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

- [ ] **Step 4: Implement `db.py`**

Async engine from `settings.database_url`, `async_sessionmaker(expire_on_commit=False)`, `Base = declarative_base()` (DeclarativeBase), `get_db()` async generator yielding a session.

- [ ] **Step 5: Init Alembic**

Run: `cd packages/core && alembic init alembic` then edit `env.py` to import `Base` and `get_settings`, configure async engine. Generate initial migration: `alembic revision --autogenerate -m "base"`. (Empty at this point; models added in Task 3 regenerate.)

- [ ] **Step 6: Run test — expect PASS**

Run: `pytest tests/core/test_db.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/core/src/anomaly_core/config.py packages/core/src/anomaly_core/db.py packages/core/alembic* tests/core/test_db.py
git commit -m "feat(core): config, database, alembic setup"
```

---

### Task 3: Domain models

**Files:**
- Create: `packages/core/src/anomaly_core/models/__init__.py`, `user.py`, `engagement.py`, `finding.py`, `run.py`, `audit.py`, `approval.py`
- Modify: `packages/core/alembic/versions/` (regenerate migration)
- Test: `tests/core/test_models.py`

**Interfaces:**
- Produces: ORM models `User`, `Role`, `Permission`, `Engagement`, `Scope`, `Target`, `Finding`, `Evidence`, `Report`, `Run`, `AuditLog`, `Approval`, `Playbook`, `PlaybookStep`. Enums: `EngagementMode`, `EngagementStatus`, `FindingSeverity`, `FindingStatus`, `RunStatus`, `RoleName`. All models expose `id: UUID` (default uuid4), `created_at`, `updated_at` (timezone-aware).

- [ ] **Step 1: Write failing tests `tests/core/test_models.py`**

Tests: create a User with hashed password field; create an Engagement with mode and status defaults; create a Finding linked to an engagement and target; create an AuditLog entry; assert `scope_warning` defaults False on Run. Each test uses an in-memory/transactional session fixture.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement models**

One file per group. Key constraints:
- `User`: id, email (unique), name, password_hash, is_active, created_at, updated_at. Relationship to roles via `UserRole`.
- `Role`/`Permission`: role name enum (admin, pentester, client_viewer); permissions as strings; many-to-many Role↔Permission.
- `Engagement`: id, name, mode (own_infra/bug_bounty/client), status (draft/active/paused/closed), owner_id (FK user), client_name (nullable), rules_of_engagement (text), start_date, end_date, created_at, updated_at.
- `Scope`: id, engagement_id (FK), notes. Relationships: in_scope_targets, out_of_scope entries (stored as `ScopeEntry` with `kind=in/out` and `target_value`).
- `Target`: id, engagement_id, value, type (domain/ip/cidr/url/service), status (active/discovered/confirmed), discovered (bool), created_at.
- `Finding`: id, engagement_id, target_id (nullable), title, severity (info/low/medium/high/critical), status (new/triaged/confirmed/fixed/false_positive), description, remediation, cvss (nullable float), reporter_id, ai_drafted (bool), reviewer_id (nullable), fingerprint (string, indexed), created_at, updated_at.
- `Evidence`: id, finding_id (nullable), run_id (nullable), type (screenshot/request_response/tool_output/log), storage_key, metadata (JSON), created_at.
- `Report`: id, engagement_id, version (int), status (draft/review/published), format (markdown/html/pdf), content (text), author_id, approver_id (nullable), published_at (nullable), created_at.
- `Run`: id, engagement_id, user_id, tool (str), target_ids (JSON array of UUIDs), params (JSON), status (queued/running/succeeded/failed/cancelled), scope_warning (bool, default False), container_id (nullable), started_at, finished_at, created_at.
- `AuditLog`: id, actor_id (nullable), action (str), resource_type, resource_id (nullable), engagement_id (nullable), metadata (JSON), created_at. No updated_at (immutable).
- `Approval`: id, resource_type, resource_id, requester_id, approver_id (nullable), status (pending/approved/rejected), reason (nullable), created_at, decided_at (nullable).
- `Playbook`: id, name, description, owner_id, steps (JSON list of `{tool, params, condition, on_failure}`), created_at, updated_at.

All FKs with appropriate ondelete. Indexes on engagement_id, status, fingerprint, created_at.

- [ ] **Step 4: Regenerate Alembic migration**

Run: `cd packages/core && alembic revision --autogenerate -m "domain models"`
Review generated file for correctness (FKs, indexes).

- [ ] **Step 5: Run tests + migration**

Run: `alembic upgrade head && pytest tests/core/test_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/anomaly_core/models packages/core/alembic tests/core/test_models.py
git commit -m "feat(core): domain models and migration"
```

---

### Task 4: Authentication (hashing, JWT, refresh rotation)

**Files:**
- Create: `packages/core/src/anomaly_core/auth.py`
- Modify: `apps/api/src/anomaly_api/routers/auth.py`, `deps.py`
- Test: `tests/api/test_auth.py`

**Interfaces:**
- Consumes: `User` model, `Settings`.
- Produces: `hash_password(plain) -> str`, `verify_password(plain, hashed) -> bool`, `create_access_token(user_id, roles) -> str`, `create_refresh_token(user_id) -> str`, `decode_token(token) -> TokenPayload`, `get_current_user` (FastAPI dependency), `require_role(*roles)` dependency factory. Endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`.

- [ ] **Step 1: Write failing tests `tests/api/test_auth.py`**

Tests (using async client + db fixture):
- register creates user and returns tokens.
- login with correct creds returns access+refresh.
- login with wrong creds returns 401.
- `/api/auth/me` with access token returns user.
- `/api/auth/me` without token returns 401.
- refresh rotates: old refresh token rejected after use.
- logout revokes refresh token.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `auth.py`**

- `hash_password`/`verify_password` via passlib bcrypt.
- JWT: access token payload `{sub, roles, type: access, exp, iat, jti}`; refresh token payload `{sub, type: refresh, exp, iat, jti, family}`. Sign with `settings.jwt_secret`, HS256.
- Refresh token family tracking for rotation: store hashed refresh token jti in a `RefreshToken` table (add to models) with `family_id`, `revoked` flag. On refresh: verify token, check not revoked, revoke old, issue new in same family. On reuse of revoked token → revoke entire family (theft detection).
- `decode_token` raises `HTTPException(401)` on invalid/expired.

- [ ] **Step 4: Implement auth router + deps**

`deps.py`: `get_db`, `get_current_user` (decodes bearer token, loads user, checks active), `require_role(*roles)`.

Router endpoints as listed. Register requires admin or first-user bootstrap (first registration allowed when no users exist; subsequent require admin). Login rate-limiting deferred.

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/anomaly_core/auth.py apps/api/src/anomaly_api/routers/auth.py apps/api/src/anomaly_api/deps.py tests/api/test_auth.py
git commit -m "feat(auth): hashing, JWT access/refresh with rotation"
```

---

### Task 5: RBAC and per-engagement access control

**Files:**
- Create: `packages/core/src/anomaly_core/rbac.py`
- Modify: `apps/api/src/anomaly_api/deps.py` (add `require_engagement_access`)
- Test: `tests/api/test_rbac.py`

**Interfaces:**
- Produces: `has_role(user, role)`, `has_permission(user, perm)`, `require_permission(perm)`, `engagement_accessible(user, engagement, min_role)` (bool), `require_engagement_access(engagement_id, min_role)` dependency. Roles seeded on first migration: admin, pentester, client_viewer with default permission sets.

- [ ] **Step 1: Write failing tests `tests/api/test_rbac.py`**

Tests:
- admin can access any engagement.
- pentester can access assigned engagements only.
- client_viewer can read assigned engagement's findings/reports only (no runs, no create).
- unassigned user gets 403 on engagement endpoints.
- cross-engagement finding read returns 404 (not 403, to avoid enumeration).

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `rbac.py`**

- Seed roles/permissions in a migration or startup hook (admin: `*`; pentester: engagements.read/write, findings.*, runs.*, reports.read; client_viewer: engagements.read, findings.read, reports.read).
- `EngagementMember` model (engagement_id, user_id, role) added to models (update Task 3 model file + new migration).
- `engagement_accessible`: admin always; otherwise check `EngagementMember` row with sufficient role rank.

- [ ] **Step 4: Add `require_engagement_access` dependency and wire into routers (engagements, findings, runs)**

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit**

---

### Task 6: Scope enforcement + audit log

**Files:**
- Create: `packages/core/src/anomaly_core/scope.py`, `packages/core/src/anomaly_core/audit.py`
- Modify: `apps/api/src/anomaly_api/routers/audit.py`
- Test: `tests/core/test_scope.py`, `tests/api/test_audit.py`

**Interfaces:**
- Produces: `check_scope(engagement, requested_targets) -> ScopeCheckResult` (in_scope: list, out_of_scope: list, has_warning: bool), `record_scope_warning(...)` audit helper. `AuditService.log(actor_id, action, resource_type, resource_id, engagement_id, metadata)`. Endpoint `GET /api/audit?engagement_id=&limit=` (admin or engagement member).

- [ ] **Step 1: Write failing tests**

Scope tests: in-scope target returns no warning; out-of-scope target returns warning with the target in `out_of_scope`; mixed returns both lists. Audit tests: creating an engagement writes an audit row; scope warning writes an audit row with action `scope.warning`; list endpoint filters by engagement and respects access.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `scope.py`**

Normalize targets (lowercase domains, strip trailing dots, parse CIDR). Compare against `Scope` in-scope and out-of-scope entries. Out-of-scope entries take precedence (a target listed in both is out of scope). Return `ScopeCheckResult`.

- [ ] **Step 4: Implement `audit.py`**

`AuditService` with async `log(...)` writing an `AuditLog` row in the same transaction as the caller when a session is passed; flush and (optionally) commit. Provide `get_audit_log(db, engagement_id, limit, offset)`.

- [ ] **Step 5: Wire audit calls into engagements/findings/runs routers** (create, update, delete, enqueue, scope warning).

- [ ] **Step 6: Run tests — expect PASS**

- [ ] **Step 7: Commit**

---

### Task 7: Engagements and findings REST API

**Files:**
- Modify: `apps/api/src/anomaly_api/routers/engagements.py`, `findings.py`
- Test: `tests/api/test_engagements.py`, `tests/api/test_findings.py`

**Interfaces:**
- Engagements: `GET/POST /api/engagements`, `GET/PATCH/DELETE /api/engagements/{id}`, `GET/PUT /api/engagements/{id}/scope`, `POST /api/engagements/{id}/targets`.
- Findings: `GET/POST /api/engagements/{id}/findings`, `GET/PATCH/DELETE /api/findings/{id}`, `POST /api/findings/{id}/status` (transition).

- [ ] **Step 1: Write failing tests** (CRUD, scope update, target add, finding create/status transition, access control).

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement routers** with Pydantic request/response schemas in `apps/api/src/anomaly_api/schemas/` (engagement, finding, scope, target). Validate mode, severity, status enums.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

---

### Task 8: Runner abstraction, worker, and vertical slice

**Files:**
- Modify: `packages/core/src/anomaly_core/runner.py`
- Create: `apps/worker/src/anomaly_worker/main.py`, `executor.py`, `tasks.py`
- Modify: `apps/api/src/anomaly_api/routers/runs.py`
- Test: `tests/api/test_runs.py`, `tests/core/test_runner.py`

**Interfaces:**
- Produces: `RunnerBackend` protocol (`async def run(self, spec: RunSpec) -> RunResult`), `DockerRunner` (spawns container, streams logs, returns exit code + stdout), `FakeRunner` (test double, records calls, returns canned result). `RunSpec`/`RunResult` dataclasses. arq task `execute_run(run_id)`. Endpoint `POST /api/engagements/{id}/runs` (enqueue), `GET /api/runs/{id}` (status), `GET /api/runs/{id}/logs` (stream or fetch).

- [ ] **Step 1: Write failing tests**

Core: `FakeRunner.run` records the spec and returns configured result; `DockerRunner` builds correct `docker run` args (network, image, env, resource limits) — test via mocking the docker SDK.

API: enqueue run → 202 with run id; status endpoint reflects queued/running/succeeded; scope warning flag set when target out of scope; audit row written on enqueue.

E2E (vertical slice): create engagement with in-scope target → enqueue stub tool run → worker (in-process, FakeRunner) executes → Run status succeeded → a Finding exists → audit log has ≥3 rows (engagement created, run enqueued, scope check). Use an in-process arq worker or call the executor directly in the test.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `runner.py`**

`RunSpec`: tool, image, target_values, params, env, timeout_s, network, resource_limits.
`RunResult`: exit_code, stdout, stderr, artifacts (list of paths), duration_s.

`DockerRunner`: uses docker SDK; container with `network=runner_network`, `mem_limit`, `cpu_period/quota`, `read_only=True` where image supports, mounts scratch volume; captures logs; removes container on completion; never `privileged=True`.

`FakeRunner`: configurable return; records `specs: list[RunSpec]`.

- [ ] **Step 4: Implement worker**

`tasks.execute_run(ctx, run_id)`: load run, load engagement+scope, run scope check (log warning if needed, set flag), set status running, call runner, store logs as Evidence, parse `ToolResult` into Findings (stub tool creates one finding), set status succeeded/failed, audit.

`executor.py`: orchestration helpers used by both worker and tests.

`main.py`: arq worker settings (functions, redis, max_jobs).

- [ ] **Step 5: Implement runs router** (enqueue via arq, or direct executor call when `RUNNER_MODE=inline` for tests/dev).

- [ ] **Step 6: Implement stub tool**

A minimal tool wrapper in `packages/tools` (create `packages/tools/src/anomaly_tools/stub.py`) that emits a `ToolResult` with one finding ("Stub finding: target reachable"). Register in a tool registry dict. (Full tool packs come in plan 2.)

- [ ] **Step 7: Run tests — expect PASS (including vertical slice)**

- [ ] **Step 8: Commit**

---

### Task 9: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write workflow**

Jobs: `lint` (ruff check + ruff format --check), `typecheck` (mypy packages apps), `test` (services postgres+redis, install, alembic upgrade, pytest with coverage), `docker` (build runner image). Use Python 3.12, uv for install.

- [ ] **Step 2: Validate locally**

Run: `act` if available, else push to a branch and check. At minimum, run `ruff check . && mypy packages apps && pytest -q` locally and confirm green.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml && git commit -m "ci: lint, typecheck, test, docker build"
```

---

## Self-Review

1. **Spec coverage:** §8 data model → Task 3. §9 auth/RBAC → Tasks 4, 5. §10 execution → Task 8. §6 scope warn-and-log → Task 6. §14 audit → Task 6. §11 AI deferred to plan 3. §12 CLI deferred to plan 4. §13 web deferred to plan 5. §15 reporting deferred to plan 6. §16 integrations deferred to plan 7. §17 standardization deferred to plan 8. No spec requirement lacks a task (within this plan's scope).
2. **Step scan:** Each step is one action with a checkable result. Test steps include assertions; code steps include signatures; verification steps include commands. No "handle edge cases" placeholders.
3. **Type consistency:** Model names, endpoint paths, and dependency names are used consistently across tasks. `RunnerBackend.run(spec: RunSpec) -> RunResult` is the single execution interface referenced by Task 8 tests and implementation.
4. **Review Focus:** All five lines have corresponding tests (cross-engagement → Task 5 tests; auth boundary → Task 4; scope context → Task 6; audit count → Task 6/8; container privileged → Task 8 DockerRunner tests).
5. **Proportion:** Plan is ~1/3 the length of the spec's foundation-relevant sections; code appears only where the spec fixes exact values (env keys, enum values, endpoint paths). Bodies are left to the implementer.

---

Plan complete and saved to `docs/superpowers/plans/2026-11-03-anomaly-foundation.md`. Please review the plan. Does it capture what you want? If so, which execution approach should we use?

- **Subagent-driven** — a fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough.
- **Native** — I implement every task myself in this session, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest.

For this plan I recommend **subagent-driven**, because the tasks have tight interface dependencies (models → auth → RBAC → scope → API → runner) where an early naming mistake would cascade, and a shipped mistake in auth or scope enforcement on a security tool is costly. Does the plan capture what you want, and which approach should we use?