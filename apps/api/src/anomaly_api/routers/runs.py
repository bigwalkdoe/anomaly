from __future__ import annotations

import os
from typing import Annotated
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, RoleName, Run, RunStatus
from anomaly_core.scope import check_scope
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access
from anomaly_api.schemas.engagement import TargetResponse  # noqa: F401

router = APIRouter(tags=["runs"])


class RunCreate(BaseModel):
    tool: str = Field(default="stub")
    targets: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: UUID
    status: str
    scope_warning: bool

    model_config = ConfigDict(from_attributes=True)


@router.get("/api/engagements/{engagement_id}/runs", response_model=list[RunResponse])
async def list_runs(
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    db: DbSession,
):
    runs = (await db.scalars(select(Run).where(Run.engagement_id == engagement.id))).all()
    return [RunResponse.model_validate(r) for r in runs]


@router.post(
    "/api/engagements/{engagement_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_run(
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    payload: RunCreate,
    user: CurrentUser,
    db: DbSession,
):
    targets = payload.targets
    try:
        from anomaly_core.models import Scope
        from sqlalchemy.orm import selectinload

        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == engagement.id)
        )
        eng_loaded = res.scalar_one()
    except Exception:
        eng_loaded = engagement
    result = check_scope(eng_loaded, targets)
    run_params = dict(payload.params or {})
    run_params["targets"] = targets  # scope-checked targets must not be overridden
    run = Run(
        engagement_id=engagement.id,
        user_id=user.id,
        tool=payload.tool,
        status=RunStatus.queued,
        scope_warning=result.has_warning,
        params=run_params,
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

    return RunResponse.model_validate(run)


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: CurrentUser, db: DbSession):
    try:
        rid = UUID(str(run_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid run_id") from None
    run = await db.get(Run, rid)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    engagement = await db.get(Engagement, run.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Run not found")
    from anomaly_core.rbac import engagement_accessible

    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.model_validate(run)
