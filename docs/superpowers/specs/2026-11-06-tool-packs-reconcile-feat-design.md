# Tool Packs Reconciliation onto `feat/tool-packs-phase2` — Design

**Date:** 2026-11-06  
**Status:** Proposed (pending approval)  
**Target:** `/home/deon/dev/github/anomaly`, branch `feat/tool-packs-phase2`  
**Source reference:** plan-as-written implementation in `.worktrees/foundation` / PR #3 (`docs/superpowers/plans/2026-11-03-anomaly-tool-packs.md`)

## Intent
Reconcile plan 2 (tool packs) onto `feat/tool-packs-phase2` by adopting the plan-aligned tool architecture while **preserving behaviors already shipped on feat**.

## Why
`feat/tool-packs-phase2` and foundation diverged: foundation matches the written plan (`base`/`Tool` protocol/`ToolSpec`/`build_cmd`/`parse`, `ToolRegistry`), while feat adds recon discovered-target auto-creation (spec 17.5), finding dedup/attach, and uses feat core/worker conventions. Reconciliation should produce one coherent, test-verified implementation without regressing feat.

## Goals
- Plan-aligned tool contract on feat: `ToolSpec`, `build_cmd`, `parse` → `ToolResult`/`FindingDraft`, `ToolRegistry`/`get_default_registry()`.
- Keep feat behaviors: **fingerprint dedup/attach** for findings and **discovered-target auto-creation** (`Target.discovered=true`).
- Keep/restore feat tool coverage: stub, nmap, nuclei, ffuf, recon/httpx, sqlmap (safe defaults + explicit risky gating + audit), generic/passthrough placeholders where appropriate.
- All relevant existing tests green (`tests/tools/*` on feat, plus affected core/worker/api tests) and new/ported plan tests added.

## Non-goals
- Full container/DockerRunner execution semantics beyond current runner contract.
- Porting unrelated `feature/foundation` web/MFA/WS work.
- Changing core schema unless required for compatibility.

## Constraints
- Preserve feat’s `execute_run_inline` semantics where valuable (scope check, evidence, dedup/attach, discovered targets, run status/audit).
- Adapt to feat’s existing core conventions/signatures (e.g. `RunStatus.QUEUED/RUNNING/SUCCEEDED/FAILED`, `AuditService.log(db, ...)` if that’s feat’s contract) — verify before changing.
- TDD for behavior changes; no regressions in `test_dedup.py`, `test_recon_targets.py`, existing parser/execution tests.
- Do not silently drop `AGENTS.md` / plan whitespace uncommitted changes; leave unrelated working-tree state intact.

## Approaches (considered)
1. **Port foundation architecture + preserve feat behaviors (chosen).** Extend plan `ToolResult`/parsing path to carry `discovered_targets`; keep dedup/attach + target auto-creation in executor; register recon/httpx/placeholders. *Tradeoff:* careful adapter work, highest correctness.
2. **Selective cherry-pick into `TOOL_DEFS`.** Lower churn, remains divergent from plan/PR #3. *Rejected as primary* given explicit reconciliation request.
3. **Replace feat stack with foundation’s.** Simple but regresses dedup/discovered-targets. *Rejected* (user requires preservation).

## Design (how)
- **`packages/tools`**: introduce/align `base.py` (`FindingDraft`, `ToolSpec`, `ToolResult` including `findings`, `evidence`/`raw`, and `discovered_targets`), `Tool` protocol, `ToolRegistry`; `get_default_registry()` registers stub, nmap, httpx/recon-compatible tool(s), nuclei, ffuf, sqlmap, and keeps passthrough/placeholder behavior for not-yet-implemented tools as needed.
- **Wrappers**: align nmap/nuclei/ffuf to `build_cmd`/`parse`; keep/port `recon` parsing to produce `discovered_targets` (and no spurious findings unless intended); `sqlmap` enforces safe defaults and `allow_risky_options` gating.
- **`apps/worker/executor`**: resolve tools via registry; build `ToolSpec` from `run.params`/targets; run via runner with command; parse output; **dedup/attach** by `(engagement,fingerprint)` as feat currently does; **create discovered `Target` rows** from `discovered_targets` (idempotent). Log risky explicit options.
- **`apps/api/runs` + `core.runner`**: ensure targets/params stored and `RunSpec.command` supported compatibly with feat.
- **Tests**: keep feat’s `test_dedup.py`, `test_recon_targets.py`, parser/execution tests passing; add/port plan-style tool tests where valuable; update expectations only where behavior is intentionally aligned (documented in commits).

## Decisions (builder calls)
- `discovered_targets` is part of the tool result contract (extension to written plan) because feat requires it and spec 17.5 behavior exists.
- `httpx` and `recon` naming: support both/alias to preserve existing runs/tests.
- Use feat’s core enum/status and audit signatures; do not import foundation-only model shapes.

## Verification
- `./.venv/bin/python -m pytest tests/tools -q` (and any updated tool test paths) green.
- `pytest tests/core -q` and relevant `tests/api` run/e2e/executor tests green in main worktree.
- Manual sanity: stub/nmap run path and recon discovered-target creation still behave as before.

## What’s left to the builder
- Exact file mapping for feat’s existing tool modules/tests vs plan names.
- Whether to keep legacy `TOOL_REGISTRY`/`TOOL_DEFS` aliases for compatibility.
- Commit granularity on `feat/tool-packs-phase2`.
