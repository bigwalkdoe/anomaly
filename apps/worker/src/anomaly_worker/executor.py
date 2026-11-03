from __future__ import annotations

from typing import Any

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from anomaly_tools.stub import stub_tool


async def execute_run(db: AsyncSession, run_id, runner: Any = None) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise ValueError("Run not found")
    run.status = RunStatus.running
    await db.flush()

    try:
        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == run.engagement_id)
        )
        engagement = res.scalar_one()
    except Exception:
        engagement = await db.get(Engagement, run.engagement_id)

    targets = []
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

    if runner is None:
        runner = FakeRunner()

    spec = RunSpec(tool=run.tool, image="anomaly-runner:dev", target_values=targets)
    runner_result = await runner.run(spec)

    ev = Evidence(
        run_id=run.id,
        type=EvidenceType.log,
        storage_key=f"logs/{run.id}.txt",
        metadata={"stdout": getattr(runner_result, "stdout", "")},
    )
    db.add(ev)

    tool_res = stub_tool(targets=targets)
    for f in getattr(tool_res, "findings", []) or []:
        finding = Finding(
            engagement_id=run.engagement_id,
            title=f.get("title", "Stub finding: target reachable"),
            severity=FindingSeverity(f.get("severity", "info")),
            description=f.get("description", ""),
            reporter_id=run.user_id,
            fingerprint=f"{run.id}:{f.get('title')}:{id(f)}",
        )
        db.add(finding)

    run.status = RunStatus.succeeded
    await AuditService.log(
        actor_id=run.user_id,
        action="run.complete",
        resource_type="run",
        resource_id=run.id,
        engagement_id=run.engagement_id,
        metadata={"status": "succeeded"},
        db=db,
    )
    await db.commit()
    await db.refresh(run)
    return run
