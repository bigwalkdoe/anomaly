from __future__ import annotations

from typing import Any
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.models import (
    Engagement,
    Evidence,
    EvidenceType,
    Finding,
    FindingSeverity,
    Run,
    RunStatus,
    Scope,
)
from anomaly_core.runner import FakeRunner, RunSpec
from anomaly_core.scope import check_scope
from anomaly_tools import ToolSpec as AnomalyToolSpec
from anomaly_tools import get_default_registry
from anomaly_tools.stub import stub_tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

RISKY_PARAM_KEYS = {"allow_risky_options", "allow_risky", "risk", "level"}


def _targets_from_run(run: Run) -> list[str]:
    params = run.params if isinstance(run.params, dict) else {}
    targets = params.get("targets")
    if isinstance(targets, list):
        return [str(t) for t in targets]
    if isinstance(targets, str) and targets:
        return [targets]
    return []


def _tool_params(run: Run) -> dict[str, Any]:
    params = run.params if isinstance(run.params, dict) else {}
    return {k: v for k, v in params.items() if k != "targets"}


def _severity(value: str) -> FindingSeverity:
    try:
        return FindingSeverity(str(value))
    except Exception:
        return FindingSeverity.info


async def execute_run(db: AsyncSession, run_id: UUID, runner: Any = None) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise ValueError("Run not found")
    run.status = RunStatus.running
    await db.flush()

    # Load engagement + scope for scope checks (foundation contract).
    try:
        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == run.engagement_id)
        )
        engagement = res.scalar_one()
    except Exception:
        engagement = await db.get(Engagement, run.engagement_id)

    targets = _targets_from_run(run)
    result = check_scope(engagement, targets)
    if result.has_warning:
        run.scope_warning = True
        await AuditService.log(
            actor_id=run.user_id,
            action="scope.warning",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            metadata={"out_of_scope": result.out_of_scope},
            db=db,
        )

    tool_params = _tool_params(run)
    # Log when risky options were explicitly requested (sqlmap safety).
    if tool_params.get("allow_risky_options"):
        await AuditService.log(
            actor_id=run.user_id,
            action="tool.risky_options",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            metadata={"tool": run.tool, "params": tool_params},
            db=db,
        )

    if runner is None:
        runner = FakeRunner()

    registry = get_default_registry()
    tool = registry.get(run.tool)

    tool_image = f"anomaly-tools-{run.tool}:dev" if run.tool != "stub" else "anomaly-runner:dev"
    command: list[str] | None = None
    if tool is not None:
        spec = AnomalyToolSpec(
            targets=targets,
            params=tool_params,
            engagement_id=str(run.engagement_id),
        )
        try:
            command = tool.build_cmd(spec)
        except Exception:
            command = None

    run_spec = RunSpec(
        tool=run.tool,
        image=tool_image,
        target_values=targets,
        params=tool_params,
        command=command,
    )
    runner_result = await runner.run(run_spec)

    stdout = getattr(runner_result, "stdout", "") or ""
    stderr = getattr(runner_result, "stderr", "") or ""
    ev = Evidence(
        run_id=run.id,
        type=EvidenceType.log,
        storage_key=f"logs/{run.id}.txt",
        metadata={
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": getattr(runner_result, "exit_code", 0),
        },
    )
    db.add(ev)

    # Parse findings via tool wrapper when available; fallback to legacy stub_tool.
    finding_drafts = []
    if tool is not None:
        parse_input = stdout
        if run.tool == "stub" and not parse_input.strip() and targets:
            parse_input = f"stub reached {targets[0]}"
        try:
            parsed = tool.parse(parse_input)
            finding_drafts = list(getattr(parsed, "findings", []) or [])
        except Exception:
            finding_drafts = []
    if not finding_drafts and run.tool == "stub":
        legacy = stub_tool(targets=targets)
        for f in getattr(legacy, "findings", []) or []:
            if isinstance(f, dict):
                finding_drafts.append(f)
    if not finding_drafts and tool is None:
        legacy = stub_tool(targets=targets)
        for f in getattr(legacy, "findings", []) or []:
            if isinstance(f, dict):
                finding_drafts.append(f)

    for f in finding_drafts:
        if isinstance(f, dict):
            title = f.get("title", "Stub finding: target reachable")
            severity = _severity(f.get("severity", "info"))
            description = f.get("description", "") or ""
            remediation = f.get("remediation")
            cvss = f.get("cvss")
            fp = f.get("fingerprint") or f"{run.id}:{title}:{description[:64]}"
        else:
            title = getattr(f, "title", "Finding")
            severity = _severity(getattr(f, "severity", "info"))
            description = getattr(f, "description", "") or ""
            remediation = getattr(f, "remediation", None)
            cvss = getattr(f, "cvss", None)
            fp = f"{run.id}:{title}:{description[:64]}"
        finding = Finding(
            engagement_id=run.engagement_id,
            title=title,
            severity=severity,
            description=description,
            remediation=remediation,
            cvss=cvss,
            reporter_id=run.user_id,
            fingerprint=fp,
        )
        db.add(finding)

    exit_code = getattr(runner_result, "exit_code", 0)
    run.status = RunStatus.succeeded if exit_code == 0 else RunStatus.failed
    await AuditService.log(
        actor_id=run.user_id,
        action="run.complete",
        resource_type="run",
        resource_id=run.id,
        engagement_id=run.engagement_id,
        metadata={"status": run.status.value, "tool": run.tool},
        db=db,
    )
    await db.commit()
    await db.refresh(run)
    return run


async def execute_run_inline(db, run_id, runner=None):
    """Compat alias for tool-pack tests."""
    return await execute_run(db, run_id, runner)
