from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_core.audit import AuditService
from anomaly_core.models.engagement import Scope, ScopeEntry
from anomaly_core.models.finding import Evidence, Finding, FindingSeverity, FindingStatus
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.runner import FakeRunner, RunSpec
from anomaly_core.scope import check_scope
from anomaly_tools.stub import TOOL_REGISTRY


async def execute_run_inline(db: AsyncSession, run_id: uuid.UUID, runner=None) -> Run:
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

    spec = RunSpec(
        tool=run.tool,
        image="anomaly-runner:dev",
        target_values=targets,
        params=run.params or {},
        env={},
        timeout_s=300,
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

    tool_fn = TOOL_REGISTRY.get(run.tool)
    if tool_fn is not None:
        tr = await tool_fn(targets, run.params)
        for f in tr.parsed_findings:
            sev = f.get("severity", "info")
            try:
                severity = FindingSeverity(sev)
            except ValueError:
                severity = FindingSeverity.INFO
            db.add(
                Finding(
                    engagement_id=run.engagement_id,
                    title=f.get("title", "Finding"),
                    severity=severity,
                    status=FindingStatus.NEW,
                    description=f.get("description"),
                    reporter_id=run.user_id,
                    fingerprint=f"{run.engagement_id}:{run.tool}:{f.get('title','')}",
                )
            )

    run.status = RunStatus.SUCCEEDED if result.exit_code == 0 else RunStatus.FAILED
    run.finished_at = datetime.now(UTC)
    await AuditService.log(
        db, run.user_id, "run.complete", "run", run.id, run.engagement_id, {"status": run.status.value}
    )
    await db.commit()
    return run
