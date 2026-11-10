# AI Suggest Tools (Real Providers + Structured Suggestions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stub AI providers with real Ollama/OpenAI/Anthropic HTTP integrations, add structured `suggest_tools` output with text fallback, and expose an authenticated API endpoint and CLI command for suggesting tools/next steps.

**Architecture:** Extend `packages/core` settings with AI config, implement provider `complete()` via `httpx.AsyncClient`, enhance `AIService.suggest_tools` to prompt/parse JSON grounded in the tool registry and log audits, add `apps/api` router + CLI `ai suggest-tools` that calls the API.

**Tech Stack:** Python 3.12, FastAPI, Typer, httpx, Pydantic v2, SQLAlchemy async, pytest/pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-11-10-ai-suggest-tools-design.md`

## Global Constraints

- Provider-agnostic AI layer; Ollama is the default provider.
- No provider SDK dependencies; use direct HTTP APIs via `httpx` (already a dependency of `anomaly-ai`).
- No hard-coded secrets; API keys/base URLs/models come from env-backed settings (`packages/core/config.py`, `.env`, `extra="ignore"`).
- Suggestions are advisory only (no tool execution); no approval gate required for suggestion calls.
- Every AI suggest call must be audit-logged (actor, optional engagement, provider/model/usage, parse outcome) with bounded prompt/response snippets (~4KB cap).
- Follow existing patterns: FastAPI routers + deps (`CurrentUser`, `DbSession`, engagement access checks), Typer command groups using the API with `--api-url`/`--token`.
- Keep public interfaces stable where reasonable; update existing `tests/ai` to work with real (mocked) provider behavior.

## Review Focus

- **Provider misconfiguration/unreachable endpoint:** API/CLI should surface a clear error (not a silent success or swallowed exception) when provider calls fail (bad key, connection refused, non-2xx).
- **Malformed/non-JSON model output:** `suggest_tools` must return a safe fallback payload with `parse_success=false` and `raw` text (no exception/crash).
- **Engagement access when `engagement_id` is supplied:** inaccessible or unknown engagement must not leak existence; enforce same access behavior as other engagement-scoped endpoints.
- **Unauthenticated AI endpoint access:** `POST /api/ai/suggest-tools` must require auth and reject missing/invalid tokens.
- **Audit logging bounds/failure mode:** prompt/response metadata must be truncated to avoid oversized rows; audit logging must not drop the suggestion result on logging issues in a way that breaks the contract unexpectedly (define consistent behavior).

---

## File Structure

- `packages/core/src/anomaly_core/config.py` — add AI configuration fields to `Settings` (env-driven defaults).
- `packages/ai/src/anomaly_ai/providers.py` — real `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider` HTTP implementations; `get_provider()` defaults from settings.
- `packages/ai/src/anomaly_ai/service.py` — `AIService.suggest_tools` builds registry-grounded prompt, parses structured JSON with fallback, returns structured result, logs `ai.suggest_tools`.
- `packages/ai/src/anomaly_ai/__init__.py` — export any new public helpers/types if needed.
- `apps/api/src/anomaly_api/routers/ai.py` — `POST /api/ai/suggest-tools` endpoint.
- `apps/api/src/anomaly_api/main.py` — register AI router and OpenAPI tag.
- `apps/cli/src/anomaly_cli/commands/ai.py` — `ai suggest-tools` command calling API and rendering output.
- `apps/cli/src/anomaly_cli/main.py` — wire `ai` command group.
- `tests/ai/test_ai.py` — update/add provider and service tests (mock HTTP).
- `tests/api/test_ai.py` — API endpoint tests (auth, structured/fallback, engagement access).
- `tests/cli/test_cli.py` (or new CLI test file if appropriate) — optional smoke coverage for `ai suggest-tools` parsing/rendering behavior if easily testable.

## Task 1: Core AI configuration

**Files:**
- Modify: `packages/core/src/anomaly_core/config.py`
- Test: `tests/core/test_config.py` (create if missing) or add to appropriate existing core test

**Interfaces:**
- Produces: `Settings` fields `ai_provider`, `ai_ollama_base_url`, `ai_ollama_model`, `ai_openai_api_key`, `ai_openai_model`, `ai_openai_base_url`, `ai_anthropic_api_key`, `ai_anthropic_model`, `ai_anthropic_base_url`, `ai_request_timeout_s` with defaults per spec.

- [ ] **Step 1: Write the failing test**

Add a test that constructs/loads settings with AI env vars (or inspects defaults) and asserts defaults: `ai_provider == "ollama"`, `ai_ollama_base_url == "http://localhost:11434"`, `ai_ollama_model == "llama3.1"`, `ai_request_timeout_s == 60`, and that keys default to empty strings.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core -k ai -v` (or the specific test path)
Expected: FAIL because fields/attributes do not exist yet.

- [ ] **Step 3: Implement AI settings in `Settings`**

Add fields to `packages/core/src/anomaly_core/config.py`:
- `ai_provider: str = "ollama"`
- `ai_ollama_base_url: str = "http://localhost:11434"`
- `ai_ollama_model: str = "llama3.1"`
- `ai_openai_api_key: str = ""`
- `ai_openai_model: str = "gpt-4o-mini"`
- `ai_openai_base_url: str = "https://api.openai.com/v1"`
- `ai_anthropic_api_key: str = ""`
- `ai_anthropic_model: str = "claude-3-5-sonnet"`
- `ai_anthropic_base_url: str = "https://api.anthropic.com/v1"`
- `ai_request_timeout_s: int = 60`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core -k ai -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/anomaly_core/config.py tests/core/test_config.py
git commit -m "feat(core): add AI provider settings"
```

## Task 2: Real provider implementations

**Files:**
- Modify: `packages/ai/src/anomaly_ai/providers.py`
- Modify: `tests/ai/test_ai.py`

**Interfaces:**
- Consumes: AI settings from `anomaly_core.config.get_settings()` (Task 1).
- Produces: `OllamaProvider.complete()`, `OpenAIProvider.complete()`, `AnthropicProvider.complete()` performing real HTTP requests via `httpx` and returning `AIResponse(content, model, usage)`; `get_provider(name=None, **kwargs)` resolves provider/config from kwargs or settings.

- [ ] **Step 1: Write the failing tests**

In `tests/ai/test_ai.py`, replace/adjust stub assertions. Add async tests that mock `httpx.AsyncClient` (e.g. monkeypatch or `respx`/mock transport if available; otherwise patch provider client method/context) to verify:
- `get_provider()` defaults to ollama provider name/model from settings.
- Ollama request posts to `{base_url}/api/chat` with `stream=false` and returns parsed `message.content` + usage.
- OpenAI request posts to `{base_url}/chat/completions` with Bearer auth and parses `choices[0].message.content`.
- Anthropic request posts to `{base_url}/messages` with `x-api-key`/`anthropic-version`/`max_tokens` and parses text content.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/ai/test_ai.py -v`
Expected: FAIL (current stubs don’t make HTTP calls / don’t match mocked behavior).

- [ ] **Step 3: Implement real providers and config-aware `get_provider()`**

Update `packages/ai/src/anomaly_ai/providers.py`:
- Providers accept config (`base_url`, `model`, `api_key`, `timeout`) and implement `async def complete(self, messages, **kwargs) -> AIResponse` using `httpx.AsyncClient(timeout=...)`.
- Ollama: payload `{"model": self.model, "messages": [{"role": m.role, "content": m.content} for m in messages], "stream": False}`; response `message.content`, usage from response if present else zeros.
- OpenAI: chat completions payload; headers include `Authorization` when key set; parse first choice message content and usage.
- Anthropic: messages payload with `max_tokens` (default 1024 unless overridden), proper headers/version; parse first text block and usage.
- `get_provider(name: str | None = None, **kwargs)` uses settings when values not supplied; if `name` is None use `settings.ai_provider`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ai/test_ai.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/ai/src/anomaly_ai/providers.py tests/ai/test_ai.py
git commit -m "feat(ai): implement real provider HTTP clients"
```

## Task 3: Structured `suggest_tools` service + audit

**Files:**
- Modify: `packages/ai/src/anomaly_ai/service.py`
- Modify: `packages/ai/src/anomaly_ai/__init__.py` (if exporting result types/helpers)
- Modify: `tests/ai/test_ai.py`

**Interfaces:**
- Consumes: `AIProvider.complete()` (Task 2), `get_default_registry()` from `anomaly_tools.registry`.
- Produces: `AIService.suggest_tools(objective, context=None, actor_id=None, engagement_id=None, **kwargs) -> dict` with keys `provider, model, suggestions, notes, raw, parse_success` (and optionally token usage if desired). Logs audit action `ai.suggest_tools` when DB provided.

- [ ] **Step 1: Write the failing tests**

Add tests in `tests/ai/test_ai.py` for `suggest_tools` using a fake provider/mocked `complete`:
- When model returns valid JSON (including fenced ```json block), result has `parse_success=True`, parsed `suggestions` list items, `notes`, `raw is None`.
- When model returns invalid/non-JSON text, result has `parse_success=False`, `suggestions == []`, `raw` containing text.
- Prompt/context includes objective and available tool names from registry (assert via captured messages).
- With a DB session/spy (or mock `AuditService.log`), audit called with action `ai.suggest_tools` and metadata including `provider`, `model`, `parse_success`, `suggestion_count`, bounded fields.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/ai/test_ai.py -v`
Expected: FAIL (current `suggest_tools` returns `AIResponse`, no parsing/audit shape).

- [ ] **Step 3: Implement structured suggest + audit logging**

Update `packages/ai/src/anomaly_ai/service.py`:
- Build system prompt describing the JSON schema and include available tools (`get_default_registry().list_tools()` and supported target types where accessible).
- Call provider, extract/parse JSON (strip code fences), validate shape; normalize suggestions entries (`tool`, `reason`, `targets_hint`, `params`, `priority`).
- Return structured dict with `provider` (provider name), `model`, `suggestions`, `notes`, `raw`, `parse_success`.
- Audit log `ai.suggest_tools` with bounded metadata (truncate prompt/response snippets to ~4096 chars). Preserve/ensure `ai.complete` behavior remains usable by existing callers if still needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ai/test_ai.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/ai/src/anomaly_ai/service.py packages/ai/src/anomaly_ai/__init__.py tests/ai/test_ai.py
git commit -m "feat(ai): add structured suggest_tools with audit logging"
```

## Task 4: API endpoint for suggest-tools

**Files:**
- Create: `apps/api/src/anomaly_api/routers/ai.py`
- Modify: `apps/api/src/anomaly_api/main.py`
- Test: `tests/api/test_ai.py`

**Interfaces:**
- Consumes: `AIService` (Task 3), `CurrentUser`, `DbSession`, engagement access patterns from `apps/api/src/anomaly_api/deps.py`.
- Produces: `POST /api/ai/suggest-tools` returning structured/fallback suggestion payload; router registered in app with tag `ai`.

- [ ] **Step 1: Write the failing API tests**

Create `tests/api/test_ai.py` (follow existing API test patterns with `client`, `db_session`, auth token helpers/fixtures) to assert:
- Unauthenticated request returns 401/403 per app behavior for protected endpoints.
- Authenticated request with `{"objective":"scan web app"}` returns 200 and expected keys (`provider`, `model`, `suggestions`, `parse_success`, `notes`/`raw` as applicable) when service/provider is mocked to return deterministic output.
- If `engagement_id` provided and user lacks access, request is rejected consistently (404/403) with existing engagement access semantics.
- Model non-JSON output path returns fallback (`parse_success=false`, `raw` present).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_ai.py -v`
Expected: FAIL (route missing).

- [ ] **Step 3: Implement AI router and register it**

Create `apps/api/src/anomaly_api/routers/ai.py`:
- Pydantic request model: `objective: str` (min length 1), optional `context: dict | None`, optional `engagement_id: UUID | None`.
- Dependency-injected handler validates engagement access when `engagement_id` provided, instantiates `AIService(provider=get_provider(), db=db)`, calls `suggest_tools(...)`, returns result.
- Register in `main.py`: import router, add OpenAPI tag `ai` with description, `app.include_router(ai.router)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_ai.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/anomaly_api/routers/ai.py apps/api/src/anomaly_api/main.py tests/api/test_ai.py
git commit -m "feat(api): add AI suggest-tools endpoint"
```

## Task 5: CLI `ai suggest-tools` command

**Files:**
- Create: `apps/cli/src/anomaly_cli/commands/ai.py`
- Modify: `apps/cli/src/anomaly_cli/main.py`
- Test: `tests/cli/test_cli.py` (extend) or `tests/cli/test_ai_cli.py` (create)

**Interfaces:**
- Consumes: API `POST /api/ai/suggest-tools` (Task 4).
- Produces: `anomaly ai suggest-tools --objective ... [--context-json ...] [--engagement-id ...] [--api-url ...] [--token ...]` rendering suggestions.

- [ ] **Step 1: Write the failing CLI test(s)**

Add tests that invoke the CLI command with mocked `httpx.post` (or patch client) to verify:
- Command is registered (`python -m anomaly_cli.main ai --help` shows `suggest-tools`).
- On structured response, output includes tool/reason/priority information.
- On fallback response (`parse_success=false`), output includes raw text.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/cli -v -k ai`
Expected: FAIL (command/group missing).

- [ ] **Step 3: Implement CLI command and wire group**

Create `apps/cli/src/anomaly_cli/commands/ai.py` with Typer app `name="ai"` and `suggest-tools` command:
- Parse `--context-json` safely (invalid JSON → user-friendly error and exit 1).
- POST to `{api_url}/api/ai/suggest-tools` with auth headers and payload.
- Render table for structured suggestions + notes; render raw text when fallback.
Wire into `apps/cli/src/anomaly_cli/main.py` with `app.add_typer(ai_app, name="ai")`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/cli -v -k ai`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cli/src/anomaly_cli/commands/ai.py apps/cli/src/anomaly_cli/main.py tests/cli
git commit -m "feat(cli): add ai suggest-tools command"
```

## Task 6: Verification and cleanup

**Files:**
- Modify: any files needed for lint/test fixes

- [ ] **Step 1: Run targeted test suites**

Run: `pytest tests/ai tests/api/test_ai.py tests/cli -v`
Expected: PASS.

- [ ] **Step 2: Run lint on changed areas**

Run: `ruff check packages/ai apps/api/src/anomaly_api/routers/ai.py apps/api/src/anomaly_api/main.py apps/cli/src/anomaly_cli/commands/ai.py apps/cli/src/anomaly_cli/main.py packages/core/src/anomaly_core/config.py`
Expected: clean (or fix issues).

- [ ] **Step 3: Run broader regression check (as feasible)**

Run: `pytest tests/core tests/ai tests/api -q` (and CLI tests) if environment/services available.
Expected: no regressions introduced by AI layer changes.

- [ ] **Step 4: Final commit (if needed)**

```bash
git add -A
git commit -m "chore: finalize AI suggest-tools implementation"
```
