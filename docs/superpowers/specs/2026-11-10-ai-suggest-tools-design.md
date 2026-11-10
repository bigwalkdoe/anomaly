# Anomaly — AI Suggest Tools (Real Providers + Structured Suggestions) Design

**Date:** 2026-11-10  
**Status:** Draft — pending approval  
**Approach:** Mix 1+2 (real providers/config/audit + structured JSON suggestions with raw-text fallback)  
**Spec reference:** `docs/superpowers/specs/2026-11-03-anomaly-design.md` §11

## 1. Intent and why
Make the AI layer usable for an end-to-end capability: suggest tools/next steps from an objective (optionally with minimal context). Replace stub provider behavior with real HTTP calls to Ollama (default), OpenAI, or Anthropic using deployment config, add structured suggestions (with text fallback), and expose via API and CLI. Keep audit logging for every AI call.

## 2. Goals
- Real provider integrations via `httpx` implementing the existing `AIProvider.complete()` interface.
- AI settings in `packages/core/config.py` (provider selection, Ollama/OpenAI/Anthropic URLs/models/keys) with env overrides.
- `AIService.suggest_tools` returns structured suggestions when the model produces JSON matching a schema; falls back to raw `AIResponse` text on parse failure.
- Authenticated API endpoint to suggest tools (objective + optional context).
- CLI command `ai suggest-tools` using the API (or service) to deliver the capability end-to-end.
- Audit logging of `ai.suggest_tools` (and/or `ai.complete`) with actor, optional engagement_id, model, usage, and prompt/response metadata (bounded).
- Ground suggestions in available tools from `packages/tools` registry.

## 3. Non-goals
- Full triage assistance or report drafting in this slice.
- Real tool execution triggered by suggestions (advisory only).
- Provider SDK dependencies (use direct HTTP APIs).
- UI changes.

## 4. Constraints
- Keep existing interfaces where reasonable (`AIProvider`, `AIService`) to avoid breaking current tests.
- No hard-coded secrets; keys via env/config.
- Follow existing patterns (FastAPI routers/deps, Typer CLI, Rich output).
- Human approval gates remain only where execution/destructive actions occur (suggestions don’t require them).

## 5. Approaches considered
- **1 (text only):** simple and fast, but less machine-consumable.
- **2 (structured only):** powerful but brittle if parsing fails with no fallback.
- **3 (engagement-context-heavy):** great relevance, more coupling/prompt size.
- **Mix 1+2 (chosen):** real providers + structured JSON with raw-text fallback, simple endpoint/CLI. Optional context can be passed by caller; engagement enrichment can be added later if needed.

## 6. Design details

### Config (packages/core)
Add AI-related settings to `Settings` (pydantic-settings, env_file `.env`, extra ignore):
- `ai_provider`: str = `ollama` (ollama|openai|anthropic)
- `ai_ollama_base_url`: str = `http://localhost:11434`
- `ai_ollama_model`: str = `llama3.1`
- `ai_openai_api_key`: str = ``
- `ai_openai_model`: str = `gpt-4o-mini`
- `ai_openai_base_url`: str = `https://api.openai.com/v1`
- `ai_anthropic_api_key`: str = ``
- `ai_anthropic_model`: str = `claude-3-5-sonnet`
- `ai_anthropic_base_url`: str = `https://api.anthropic.com/v1`
- `ai_request_timeout_s`: int = 60

### Providers (packages/ai)
Replace stubs with real implementations using `httpx.AsyncClient`:
- **Ollama:** `POST {base_url}/api/chat` with `model`, `messages` (role/content), `stream: false`. Parse `message.content` and usage if present.
- **OpenAI:** `POST {base_url}/chat/completions` with `model`, `messages`. Parse `choices[0].message.content` and `usage`. Support API key via `Authorization: Bearer`.
- **Anthropic:** `POST {base_url}/messages` with `model`, `messages`, `max_tokens` (required, default 1024). Map roles/content appropriately. Support `x-api-key` and `anthropic-version`. Parse `content[0].text` and `usage`.
Keep `AIMessage`/`AIResponse` (include `usage` when available). `get_provider(name, **kwargs)` reads defaults from `get_settings()` when kwargs not provided (so env config works out of the box). Errors from providers propagate as exceptions (API returns 502/500 as appropriate).

### Service (packages/ai)
Extend `AIService`:
- `suggest_tools(objective: str, context: dict | None = None, actor_id=None, engagement_id=None, **kwargs)` builds a system prompt listing available tools from `get_default_registry().list_tools()` (include supported target types when available) and asks for JSON suggestions matching schema:
  ```json
  {"suggestions": [{"tool": "...", "reason": "...", "targets_hint": "...", "params": {}, "priority": "low|medium|high"}], "notes": "..."}
  ```
- Attempt to extract/parse JSON from the model output (handle fenced code blocks). If successful and valid, return a structured dict/model:
  `{"provider": str, "model": str, "suggestions": [...], "notes": str|None, "raw": None, "parse_success": true}`.
  If parsing/validation fails, return fallback:
  `{"provider": str, "model": str, "suggestions": [], "notes": None, "raw": "<model text>", "parse_success": false}`.
- Log audit action `ai.suggest_tools` (and retain/route through `ai.complete` logging as appropriate) with bounded metadata: provider, model, usage, `engagement_id`, `objective_len`, `parse_success`, `suggestion_count`, and truncated prompt/response snippets (cap ~4KB each) to avoid oversized audit rows.

### API (apps/api)
Add router `routers/ai.py` with `POST /api/ai/suggest-tools`:
- Auth required (`CurrentUser`). Request body: `{"objective": str, "context": dict | null = None, "engagement_id": UUID | null = None}`.
- If `engagement_id` is provided, validate access using existing engagement access/RBAC patterns (same as other engagement-scoped operations); inaccessible/unknown engagement returns 404/403 consistently with the app.
- Calls `AIService` (provider from config) with DB session for audit logging. Returns 200 with the structured/fallback payload from the service.
- Register router in `apps/api/src/anomaly_api/main.py`.

### CLI (apps/cli)
Add `ai` command group (`apps/cli/src/anomaly_cli/commands/ai.py`) with `suggest-tools`:
- Options: `--objective` (required), `--context-json` (optional), `--engagement-id` (optional), plus `--api-url`/`--token` like other commands.
- Calls the API endpoint (consistent with existing CLI commands). Displays structured suggestions in a table (tool, priority, reason, targets_hint, params summary) and notes; if `parse_success` is false, prints `raw` text.
- Wire into `main.py` as `app.add_typer(ai_app, name="ai")`.

## 7. Testing
- Update/add tests in `tests/ai/` for real provider behavior (mock httpx/responses as appropriate) and structured parse + fallback in `suggest_tools`.
- Add API test for `/api/ai/suggest-tools` (auth required, valid/invalid JSON from model → structured/fallback response).
- Keep existing AI tests passing by preserving public interfaces where possible (or updating them to match real behavior with mocks).

## 8. Builder's calls (settled in review)
- **CLI uses API** (not direct service/DB access), consistent with existing commands.
- **Engagement access:** if `engagement_id` is provided, enforce the same access checks as other engagement operations.
- **Audit size bound:** truncate prompt/response snippets to ~4KB each in metadata; always log provider/model/usage/parse outcome.
- **Prompt grounding:** include tool names and supported target types from the registry; no extra project context beyond `objective`/`context` in this slice.
- **Provider errors:** surface as API errors (no silent swallow) so callers can see misconfiguration/connectivity issues.

## 9. Approval
Pending. Once approved, next step is `superpowers:writing-plans`.
