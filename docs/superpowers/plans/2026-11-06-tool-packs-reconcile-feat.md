# Tool Packs Reconciliation (feat/tool-packs-phase2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile plan-aligned tool packs onto `feat/tool-packs-phase2` in `/home/deon/dev/github/anomaly`, adopting `base`/`ToolSpec`/`build_cmd`/`parse`/`ToolRegistry` while preserving feat behaviors: finding dedup/attach and recon discovered-target auto-creation.

**Architecture:** Extend the plan tool contract with `discovered_targets` on `ToolResult` (and parser outputs) so `execute_run_inline` can keep spec 17.5 target auto-creation and feat dedup. Adapt all wiring to feat core conventions (`RunStatus.QUEUED/RUNNING/SUCCEEDED/FAILED`, `check_scope(entries, targets)`, `AuditService.log(db, actor, action, resource, resource_id, engagement_id, metadata)`), not foundation conventions. TDD per behavior change.

**Tech Stack:** Python 3.12, pytest/pytest-asyncio, SQLAlchemy 2.0 async, Pydantic/FastAPI, existing `anomaly_core.runner`/`anomaly_tools`.

**Spec:** `docs/superpowers/specs/2026-11-06-tool-packs-reconcile-feat-design.md` (and plan reference `docs/superpowers/plans/2026-11-03-anomaly-tool-packs.md`).

## Global Constraints
- Preserve feat behaviors: dedup/attach findings by `(engagement_id, fingerprint)` (existing finding updated, no duplicate) and auto-create discovered `Target` rows (idempotent) from tool `discovered_targets`.
- Keep feat core signatures: `check_scope(entries, targets) -> ScopeCheckResult`; `AuditService.log(db, actor_id, action, resource_type, resource_id, engagement_id, metadata)`; `RunStatus.QUEUED/RUNNING/SUCCEEDED/FAILED`.
- `RunSpec` on feat currently requires `(tool,image,target_values,params,env,timeout_s,network,resource_limits=...)` and has no `command`; add `command: list[str] | None = None` compatibly if needed, without breaking existing call sites.
- Scope check before/around execution; out-of-scope => warn + audit + `scope_warning=true` (existing behavior).
- sqlmap: detection-only safe defaults; `--level/--risk` only with explicit `allow_risky_options`; risky explicit use logged in audit.
- Do not modify/commit unrelated uncommitted files: `AGENTS.md`, `docs/superpowers/plans/2026-11-03-anomaly-foundation.md` (whitespace).

## Review Focus
1. **Dedup regression:** same `(engagement_id,fingerprint)` from repeated runs must attach/update, not create duplicates — verify `tests/tools/test_dedup.py` and executor path.
2. **Discovered target regression:** recon/httpx structured output must create `Target(discovered=True, status='discovered')` idempotently — verify `tests/tools/test_recon_targets.py`.
3. **Convention mismatch:** using foundation-style `AuditService.log` kwargs, `RunStatus.running`, or `check_scope(engagement,targets)` on feat will break runtime/tests — verify signatures at call sites.
4. **Scope/targets integrity:** API/executor must use the same scope-checked targets list (no `payload.params['targets']` override of checked targets).
5. **Empty/malformed tool output:** parsers/registry must not raise uncaught exceptions or drop all safety (e.g. sqlmap risky flags) on weird input; executor should degrade to evidence/no-findings rather than crash the run.

## File Structure
- `packages/tools/src/anomaly_tools/base.py` (new/replace): `FindingDraft`, `ToolSpec`, `ToolResult(findings,evidence,raw,discovered_targets)`, `Tool` protocol (`name`, `supported_target_types`, `build_cmd`, `parse`).
- `packages/tools/src/anomaly_tools/registry.py` (replace): `ToolRegistry` + `get_default_registry()`; compat exports if needed.
- `packages/tools/src/anomaly_tools/stub.py`, `nmap.py`, `nuclei.py`, `ffuf.py`, `sqlmap.py`, `recon.py` (align): implement `build_cmd`/`parse` returning `ToolResult` with `discovered_targets` where applicable; keep `parse_*`/`run_*` compat helpers used by existing tests if feasible.
- `packages/tools/src/anomaly_tools/generic.py` (keep/adapt): passthrough/placeholder behavior.
- `packages/tools/src/anomaly_tools/__init__.py`: export base/registry/tools.
- `packages/core/src/anomaly_core/runner.py`: add optional `command` to `RunSpec` compatibly.
- `apps/worker/src/anomaly_worker/executor.py`: registry-driven execution + preserved dedup/attach + discovered-target creation, feat audit/scope/status conventions.
- `apps/api/src/anomaly_api/routers/runs.py`: ensure targets/params persisted safely (authoritative targets).
- `tests/tools/*`: preserve existing feat tests; add/align plan-style tests (`test_registry.py`, `test_sqlmap.py`, etc.) to new interfaces.

---

### Task 1: Tool base types with `discovered_targets` and registry

**Files:**
- Create: `packages/tools/src/anomaly_tools/base.py`
- Modify: `packages/tools/src/anomaly_tools/registry.py`
- Modify: `packages/tools/src/anomaly_tools/__init__.py`
- Test: `tests/tools/test_registry.py` (create)

**Interfaces:**
- Produces: `FindingDraft(title,severity='info',description='',remediation=None,cvss=None,metadata={})`, `ToolResult(findings=[],evidence=[],raw='',discovered_targets=[])`, `ToolSpec(targets=[],params={},engagement_id=None)`, `Tool` protocol with `build_cmd(spec)->list[str]`, `parse(stdout)->ToolResult`; `ToolRegistry.register/get/list_tools`; `get_default_registry()`.

- [ ] **Step 1: Write failing `tests/tools/test_registry.py`**
```python
from anomaly_tools.base import FindingDraft, ToolResult, ToolSpec
from anomaly_tools.registry import ToolRegistry


class Dummy:
    name = "dummy"
    supported_target_types = ["domain"]

    def build_cmd(self, spec: ToolSpec):
        return ["echo", spec.targets[0] if spec.targets else ""]

    def parse(self, stdout: str):
        return ToolResult(findings=[FindingDraft(title="t")], raw=stdout, discovered_targets=[])


def test_registry_register_get_list():
    reg = ToolRegistry()
    d = Dummy()
    reg.register(d)
    assert reg.get("dummy") is d
    assert "dummy" in reg.list_tools()


def test_toolresult_has_discovered_targets():
    r = ToolResult(findings=[], discovered_targets=[{"value": "https://a.example", "type": "url"}])
    assert r.discovered_targets[0]["value"] == "https://a.example"
```
- [ ] **Step 2: Run test to verify FAIL** — `cd /home/deon/dev/github/anomaly && ./.venv/bin/python -m pytest tests/tools/test_registry.py -q` → import/module failures.
- [ ] **Step 3: Implement `base.py` and `ToolRegistry`** (preserve compat by also exporting `TOOL_DEFS`/`TOOL_REGISTRY` names if existing code imports them; can be thin wrappers over registry/tools).
- [ ] **Step 4: Run test to verify PASS**
- [ ] **Step 5: Commit** `git add packages/tools/src/anomaly_tools/base.py packages/tools/src/anomaly_tools/registry.py packages/tools/src/anomaly_tools/__init__.py tests/tools/test_registry.py && git commit -m "feat(tools): add base tool contract and registry (with discovered_targets)"`

---

### Task 2: Align stub and wrappers (nmap/nuclei/ffuf/sqlmap/recon) to plan + feat compat

**Files:**
- Modify: `packages/tools/src/anomaly_tools/stub.py`, `nmap.py`, `nuclei.py`, `ffuf.py`, `sqlmap.py`, `recon.py`, `generic.py`
- Modify: `packages/tools/src/anomaly_tools/registry.py`, `__init__.py`
- Test: `tests/tools/test_nmap_parser.py`, `test_nuclei_parser.py`, `test_ffuf_parser.py`, `test_recon_targets.py`, plus add `tests/tools/test_sqlmap.py`

**Interfaces:**
- Consumes: Task 1 base types.
- Produces: tool classes/functions with `build_cmd`/`parse`; `parse_nmap_xml`/`parse_nuclei_output`/`parse_ffuf_json`/`parse_recon_output` keep working (return `ToolResult` with `parsed_findings` alias or `findings` as feat tests expect — adapt compat layer); recon `parse`/`parse_recon_output` populates `discovered_targets`; sqlmap gates `level/risk` behind `allow_risky_options`.

- [ ] **Step 1: Write/adjust failing tests for new contract edges**
  - Add `tests/tools/test_sqlmap.py` (safe defaults, `--batch`, risky options require `allow_risky_options`) — expect FAIL on current feat sqlmap.
  - Ensure `test_recon_targets.py::test_parse_recon_output_discovers_targets` still targets a supported API (`parse_recon_output(...).discovered_targets` or `.discovered_targets` on `ToolResult`).
- [ ] **Step 2: Run targeted tests to verify failures** — `pytest tests/tools/test_sqlmap.py tests/tools/test_recon_targets.py -q`.
- [ ] **Step 3: Implement wrappers**: add `NmapTool/NucleiTool/FfufTool/SqlmapTool/StubTool/ReconTool` (or Httpx alias) with `build_cmd`/`parse`; keep legacy `parse_*` helpers returning `ToolResult` (with `discovered_targets` and compat attributes like `parsed_findings` if existing code/tests use them); `recon` maps json-lines to `discovered_targets` (type/status/discovered/metadata), `findings=[]` unless specified; sqlmap safe+risky gating.
- [ ] **Step 4: Run** `pytest tests/tools/test_nmap_parser.py tests/tools/test_nuclei_parser.py tests/tools/test_ffuf_parser.py tests/tools/test_recon_targets.py tests/tools/test_sqlmap.py -q` → PASS.
- [ ] **Step 5: Commit** tool wrapper alignment.

---

### Task 3: Runner/API target+command compatibility (feat conventions)

**Files:**
- Modify: `packages/core/src/anomaly_core/runner.py`
- Modify: `apps/api/src/anomaly_api/routers/runs.py`
- Test: `tests/core/test_runner.py` (if exists; else add minimal), existing run/e2e tests as regression.

**Interfaces:**
- Produces: `RunSpec` accepts optional `command: list[str] | None = None` without breaking existing instantiation patterns; API stores authoritative `targets` in `run.params` and does not let `body.params['targets']` override scope-checked targets.

- [ ] **Step 1: Write failing/guard test** for `RunSpec(..., command=[...])` compatibility (and existing no-command still works) in core runner tests location if present; or assert in a quick unit test.
- [ ] **Step 2: Run to confirm RED/GREEN baseline**.
- [ ] **Step 3: Implement** `command` field default `None`; in runs API set `params = {**(body.params or {})}; params['targets']=targets` (authoritative).
- [ ] **Step 4: Run core runner tests + `pytest tests/api/test_runs.py tests/api/test_runs_e2e.py -q` (if present on feat)**
- [ ] **Step 5: Commit**.

---

### Task 4: Wire executor to registry while preserving dedup/attach and discovered targets

**Files:**
- Modify: `apps/worker/src/anomaly_worker/executor.py`
- Modify: `packages/tools/src/anomaly_tools/registry.py`/`__init__.py` as needed for lookup
- Test: `tests/tools/test_dedup.py`, `tests/tools/test_recon_targets.py`, `tests/tools/test_tool_execution.py`

**Interfaces:**
- Consumes: Task 1-3; feat `check_scope(entries,targets)`, `AuditService.log(db,...)`, `RunStatus.*`, `FakeRunner`/`RunSpec`.
- Produces: `execute_run_inline(db, run_id, runner=None)` (and keep `execute_run` name if API imports it — add alias) that: loads run/scope entries, checks scope + audits warning, marks RUNNING, builds `ToolSpec` from `run.params.targets`/tool params, resolves tool via `get_default_registry()` (fallback to legacy parse/run helpers as needed), sets `RunSpec` incl. `command`, runs, stores evidence, parses findings + `discovered_targets`; **creates `Target` rows idempotently** for discovered targets; **dedups findings** on `(engagement_id,fingerprint)` updating existing record; logs `tool.risky_options` when `allow_risky_options` explicit; sets SUCCEEDED/FAILED + audits `run.complete`.

- [ ] **Step 1: Run existing feat behavior tests to establish baseline** — `pytest tests/tools/test_dedup.py tests/tools/test_recon_targets.py tests/tools/test_tool_execution.py -q` (expect PASS now; keep them passing).
- [ ] **Step 2: Write any missing failing test** for registry-based stub/nmap path if Task 4 changes break resolution (use FakeRunner stdout patterns feat tests use).
- [ ] **Step 3: Implement executor refactor** carefully; preserve dedup query/attach and discovered-target idempotent insert logic; keep feat audit/log/status signatures.
- [ ] **Step 4: Run** `pytest tests/tools/test_dedup.py tests/tools/test_recon_targets.py tests/tools/test_tool_execution.py tests/tools/test_registry.py tests/tools/test_sqlmap.py -q` → PASS.
- [ ] **Step 5: Commit**.

---

### Task 5: Full tool-suite + regression verification

**Files:**
- Modify only if required by failures: tests/tools/*, minimal compat shims.
- Test: all `tests/tools`, then affected core/api.

**Interfaces:**
- Produces: green reconciliation with no unrelated file commits.

- [ ] **Step 1: Run** `cd /home/deon/dev/github/anomaly && ./.venv/bin/python -m pytest tests/tools -q` → all PASS (record count).
- [ ] **Step 2: Run regressions** `./.venv/bin/python -m pytest tests/core/test_runner.py tests/api/test_runs.py tests/api/test_runs_e2e.py -q` (skip missing files with note).
- [ ] **Step 3: Fix only regressions caused by this reconciliation** (TDD for any fix).
- [ ] **Step 4: Re-run verification commands** → PASS.
- [ ] **Step 5: Commit** any final compat fixes; ensure `git status` does not stage `AGENTS.md` or foundation plan whitespace unless explicitly requested.

## Self-Review
1. **Spec coverage:** base/registry/build_cmd/parse (T1-2), wrappers incl. sqlmap safety (T2), wiring+dedup+discovered targets preserved (T4), target/command compat (T3), verification (T5).
2. **Step scan:** each step has command/assertion or concrete artifact; no “handle edge cases” placeholders.
3. **Type consistency:** `ToolResult` must satisfy both new `.findings`/`.discovered_targets` and any legacy `.parsed_findings` access used on feat — add compat property if needed.
4. **Review Focus:** covered by T4/T5 tests + explicit integrity fix in T3.
5. **Proportion:** plan specifies decisions/interfaces, not full bodies.

Plan complete and saved to `docs/superpowers/plans/2026-11-06-tool-packs-reconcile-feat.md`. Please review the plan. Does it capture what you want?

- **Subagent-driven** — fresh subagent per task + reviews; most thorough for tight cross-package interface changes.
- **Native** — I implement all tasks in this session with TDD, then one final whole-branch review; fastest/cheapest.

For this plan I recommend **Native** (executing-plans), because there are 5 tightly coupled tasks in one session with fast local feedback from existing `tests/tools`/core/api tests, and you’ve been directing execution interactively; the main risk (core/worker convention mismatch) is mitigated by TDD and targeted regressions. Which execution approach should we use?