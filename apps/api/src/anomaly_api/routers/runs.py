from __future__ import annotations

from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, RoleName, Run, RunStatus
from anomaly_core.scope import check_scope
from fastapi import APIRouter, Depends, status

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(tags=["runs"])


@router.get("/api/engagements/{engagement_id}/runs")
async def list_runs(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
):
    return []


@router.post("/api/engagements/{engagement_id}/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))],
    payload: dict,
    user: CurrentUser,
    db: DbSession,
):
    targets = payload.get("targets", [])
    result = check_scope(engagement, targets)
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
    return {"id": str(run.id), "status": run.status.value, "scope_warning": run.scope_warning}
