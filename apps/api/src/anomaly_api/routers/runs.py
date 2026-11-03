from __future__ import annotations

import os
from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, RoleName, Run, RunStatus
from anomaly_core.scope import check_scope
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(tags=["runs"])


@router.get("/api/engagements/{engagement_id}/runs")
async def list_runs(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    db: DbSession,
):
    runs = (await db.scalars(select(Run).where(Run.engagement_id == engagement.id))).all()
    return [{"id": str(r.id), "status": r.status.value, "scope_warning": r.scope_warning} for r in runs]


@router.post("/api/engagements/{engagement_id}/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    payload: dict,
    user: CurrentUser,
    db: DbSession,
):
    targets = payload.get("targets", [])
    try:
        from sqlalchemy.orm import selectinload
        from anomaly_core.models import Scope

        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == engagement.id)
        )
        eng_loaded = res.scalar_one()
    except Exception:
        eng_loaded = engagement
    result = check_scope(eng_loaded, targets)
    run = Run(
        engagement_id=engagement.id,
        user_id=user.id,
        tool=payload.get("tool", "stub"),
        status=RunStatus.queued,
        scope_warning=result.has_warning,
    )
    db.add(run)
    await db.flush()
    if result.has_warning:
        await AuditService.log(
            actor_id=user.id,
            action="scope.warning",
            resource_type="run",
            resource_id=run.id,
            engagement_id=engagement.id,
            metadata={"targets": targets, "out_of_scope": result.out_of_scope},
            db=db,
        )
    await AuditService.log(
        actor_id=user.id,
        action="run.enqueue",
        resource_type="run",
        resource_id=run.id,
        engagement_id=engagement.id,
        metadata={"tool": run.tool, "targets": targets},
        db=db,
    )
    await db.commit()
    await db.refresh(run)

    if os.environ.get("RUNNER_MODE") == "inline" or os.environ.get("ANOMALY_INLINE_RUNS") == "1":
        try:
            from anomaly_worker.executor import execute_run

            async with SessionLocal() as db2:
                await execute_run(db2, run.id)
        except Exception:
            pass

    return {"id": str(run.id), "status": run.status.value, "scope_warning": run.scope_warning}


@router.get("/api/runs/{run_id}")
async def get_run(run_id: str, user: CurrentUser, db: DbSession):
    from uuid import UUID

    try:
        rid = UUID(str(run_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run_id")
    run = await db.get(Run, rid)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    engagement = await db.get(Engagement, run.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Run not found")
    from anomaly_core.rbac import engagement_accessible

    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": str(run.id), "status": run.status.value, "scope_warning": run.scope_warning}
