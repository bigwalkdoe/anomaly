# Anomaly Tool Packs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real, containerized tool wrappers for nmap, nuclei, ffuf, sqlmap, httpx/recon with a registry, normalized `ToolResult`, safe defaults, and tests proving each wrapper maps params to CLI args and produces findings/evidence.

**Architecture:** Extend `packages/tools` with tool implementations under `anomaly_tools/pack_*` modules, a `ToolRegistry`, and a `ToolResult` schema shared with worker. Runners execute in isolated containers via `RunnerBackend`. Scope enforcement still applies before execution.

**Tech Stack:** Python 3.12, pydantic v2, pytest, docker (mocked in tests)

**Spec:** `docs/superpowers/specs/2026-11-03-anomaly-design.md`


## File Structure (tool packs)

```
anomaly/
├── packages/
│   ├── tools/
│   │   └── src/anomaly_tools/
│   │       ├── __init__.py
│   │       ├── base.py        # Tool protocol, ToolResult, FindingDraft
│   │       ├── registry.py    # ToolRegistry
│   │       ├── nmap.py
│   │       ├── httpx.py
│   │       ├── nuclei.py
│   │       ├── ffuf.py
│   │       ├── sqlmap.py
│   │       └── stub.py        # keep for compat
│   └── core/
└── tests/
    ├── tools/
    └── api/
```

---

### Task 1: Tool base types and registry

**Files:**
- Create: `packages/tools/src/anomaly_tools/base.py`, `packages/tools/src/anomaly_tools/registry.py`
- Modify: `packages/tools/src/anomaly_tools/__init__.py`
- Test: `tests/tools/test_registry.py`

**Interfaces:**
- `ToolResult(findings: list[FindingDraft], evidence: list[dict], raw: str)`, `FindingDraft(title, severity, description, ...)`
- `Tool` protocol with `name`, `supported_target_types`, `build_cmd(spec: ToolSpec) -> list[str]`, `parse(stdout: str) -> ToolResult`
- `ToolRegistry` with `register`, `get`, `list_tools()`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Implement base + registry**
- [ ] **Step 3: Run tests and commit**

---

### Task 2: nmap wrapper

**Files:**
- Create: `packages/tools/src/anomaly_tools/nmap.py`
- Test: `tests/tools/test_nmap.py`

**Behavior:**
- Map params (ports, top_ports, timing, scan_type) to safe nmap args
- Parse open ports/services into findings
- Never run with dangerous scripts by default

- [ ] **Step 1: Write tests (param mapping + parsing)**
- [ ] **Step 2: Implement and commit**

---

### Task 3: httpx/recon wrapper

**Files:**
- Create: `packages/tools/src/anomaly_tools/httpx.py`
- Test: `tests/tools/test_httpx.py`

- [ ] **Step 1: Tests**
- [ ] **Step 2: Implement**
- [ ] **Step 3: Commit**

---

### Task 4: nuclei wrapper

**Files:**
- Create: `packages/tools/src/anomaly_tools/nuclei.py`
- Test: `tests/tools/test_nuclei.py`

- [ ] **Step 1: Tests**
- [ ] **Step 2: Implement**
- [ ] **Step 3: Commit**

---

### Task 5: ffuf wrapper

**Files:**
- Create: `packages/tools/src/anomaly_tools/ffuf.py`
- Test: `tests/tools/test_ffuf.py`

- [ ] **Step 1: Tests**
- [ ] **Step 2: Implement**
- [ ] **Step 3: Commit**

---

### Task 6: sqlmap wrapper (safe defaults)

**Files:**
- Create: `packages/tools/src/anomaly_tools/sqlmap.py`
- Test: `tests/tools/test_sqlmap.py`

**Constraints:**
- Default to detection only, batch mode, non-destructive where possible
- Explicit param required for risky options; logged in audit

- [ ] **Step 1: Tests**
- [ ] **Step 2: Implement**
- [ ] **Step 3: Commit**

---

### Task 7: Wire registry into worker/API

**Files:**
- Modify: `apps/worker/src/anomaly_worker/executor.py`
- Modify: `packages/tools/src/anomaly_tools/__init__.py`
- Test: `tests/tools/test_integration.py`

- [ ] **Step 1: Wire and test end-to-end with stub/nmap**
- [ ] **Step 2: Commit**
