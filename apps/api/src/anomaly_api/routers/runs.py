from __future__ import annotations

from typing import Annotated
from uuid import UUID

from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, RoleName, Run
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from anomaly_api.assessment import (
    enforce_assessment_policy,
    enqueue_assessment_run,
    inline_execution_enabled,
    load_engagement_with_scope,
)
from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access
from anomaly_api.schemas.engagement import TargetResponse  # noqa: F401
from anomaly_api.tenancy import (
    child_organization_matches_engagement,
    child_organization_matches_engagement_sql,
)

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
    runs = (
        await db.scalars(
            select(Run)
            .where(Run.engagement_id == engagement.id)
            .where(child_organization_matches_engagement_sql(Run))
        )
    ).all()
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
    targets = list(payload.targets or [])
    eng_loaded = await load_engagement_with_scope(db, engagement.id) or engagement
    decision = await enforce_assessment_policy(
        db, user, engagement, targets, scope_engagement=eng_loaded, source="api.legacy"
    )

    run = await enqueue_assessment_run(
        db,
        user=user,
        engagement=engagement,
        tool=payload.tool,
        targets=targets,
        params=dict(payload.params or {}),
        policy_decision=decision,
    )

    if inline_execution_enabled():
        try:
            from anomaly_worker.executor import execute_run

            async with SessionLocal() as db2:
                await execute_run(db2, run.id)
        except Exception:  # nosec B110 - inline run failures must not break enqueue response
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
    from anomaly_core.rbac import engagement_accessible

    # Hide existence from non-members, cross-tenant callers, and mismatched child orgs.
    if (
        engagement is None
        or not child_organization_matches_engagement(run, engagement)
        or not await engagement_accessible(db, user, engagement, min_role=RoleName.client_viewer)
    ):
        raise HTTPException(status_code=404, detail="Run not found")
    # Runs are not readable by client_viewer members.
    if not await engagement_accessible(db, user, engagement, min_role=RoleName.pentester):
        raise HTTPException(status_code=403, detail="Forbidden")
    return RunResponse.model_validate(run)
