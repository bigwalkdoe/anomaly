from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from anomaly_core.audit import AuditService
from anomaly_core.models.engagement import Scope, ScopeEntry, Target
from anomaly_core.models.finding import Evidence, Finding, FindingSeverity, FindingStatus
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.runner import FakeRunner, RunSpec
from anomaly_core.scope import check_scope
from anomaly_tools.registry import TOOL_DEFS
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def execute_run_inline(db: AsyncSession, run_id: uuid.UUID, runner: Any | None = None) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise ValueError("run not found")

    scope = await db.scalar(select(Scope).where(Scope.engagement_id == run.engagement_id))
    entries = []
    if scope:
        rows = await db.scalars(select(ScopeEntry).where(ScopeEntry.scope_id == scope.id))
        entries = list(rows)
    targets = run.params.get("targets", []) if isinstance(run.params, dict) else []
    check = check_scope(entries, targets)
    if check.has_warning and not run.scope_warning:
        run.scope_warning = True
        await AuditService.log(
            db,
            run.user_id,
            "scope.warning",
            "run",
            run.id,
            run.engagement_id,
            {"out_of_scope": check.out_of_scope},
        )

    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(UTC)
    await db.flush()

    if runner is None:
        runner = FakeRunner()

    tool_def = TOOL_DEFS.get(run.tool)
    image = tool_def.image if tool_def else "anomaly-runner:dev"
    timeout_s = tool_def.default_timeout_s if tool_def else 300

    spec = RunSpec(
        tool=run.tool,
        image=image,
        target_values=targets,
        params=run.params or {},
        env={},
        timeout_s=timeout_s,
        network="anomaly-net",
    )
    result = await runner.run(spec)

    db.add(
        Evidence(
            run_id=run.id,
            type="tool_output",
            storage_key=f"inline://runs/{run.id}/stdout",
            meta={"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.exit_code},
        )
    )

    parsed: list[dict[str, Any]] = []
    discovered: list[dict[str, Any]] = []
    tr = None
    if tool_def and tool_def.parse_output and result.stdout:
        tr = tool_def.parse_output(
            result.stdout, result.stderr, result.exit_code, targets, run.params
        )
    elif tool_def and tool_def.run_direct:
        tr = await tool_def.run_direct(targets, run.params)
    else:
        from anomaly_tools.stub import TOOL_REGISTRY

        tool_fn = TOOL_REGISTRY.get(run.tool)
        if tool_fn is not None:
            tr = await tool_fn(targets, run.params)
    if tr is not None:
        parsed = tr.parsed_findings
        discovered = getattr(tr, "discovered_targets", []) or []

    for t in discovered:
        value = str(t.get("value") or "").strip()
        if not value:
            continue
        ttype = str(t.get("type") or "domain")
        exists = await db.scalar(
            select(Target).where(
                Target.engagement_id == run.engagement_id,
                Target.value == value,
                Target.type == ttype,
            )
        )
        if exists is None:
            db.add(
                Target(
                    engagement_id=run.engagement_id,
                    value=value,
                    type=ttype,
                    status=str(t.get("status") or "discovered"),
                    discovered=bool(t.get("discovered", True)),
                )
            )

    for f in parsed:
        sev = f.get("severity", "info")
        try:
            severity = FindingSeverity(sev)
        except ValueError:
            severity = FindingSeverity.INFO
        fingerprint = str(
            f.get("fingerprint") or f"{run.engagement_id}:{run.tool}:{f.get('title', '')}"
        )
        existing = await db.scalar(
            select(Finding).where(
                Finding.engagement_id == run.engagement_id,
                Finding.fingerprint == fingerprint,
            )
        )
        if existing is not None:
            # Attach: keep existing finding; optionally refresh metadata.
            existing.updated_at = datetime.now(UTC)
            continue
        db.add(
            Finding(
                engagement_id=run.engagement_id,
                title=f.get("title", "Finding"),
                severity=severity,
                status=FindingStatus.NEW,
                description=f.get("description"),
                remediation=f.get("remediation"),
                reporter_id=run.user_id,
                fingerprint=fingerprint,
            )
        )

    run.status = RunStatus.SUCCEEDED if result.exit_code == 0 else RunStatus.FAILED
    run.finished_at = datetime.now(UTC)
    await AuditService.log(
        db,
        run.user_id,
        "run.complete",
        "run",
        run.id,
        run.engagement_id,
        {"status": run.status.value},
    )
    await db.commit()
    return run
