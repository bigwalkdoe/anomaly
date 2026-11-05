from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_api.deps import get_current_user, get_db, require_engagement_access
from anomaly_core.audit import AuditService
from anomaly_core.models.engagement import Engagement, EngagementMember, Scope, ScopeEntry
from anomaly_core.models.finding import Evidence
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.models.user import User
from anomaly_core.rbac import can_access_engagement, is_admin
from anomaly_core.scope import check_scope

engagement_runs_router = APIRouter(prefix="/api/engagements", tags=["runs"])
runs_router = APIRouter(prefix="/api/runs", tags=["runs"])

# Back-compat export name used by main.py earlier.
router = engagement_runs_router


class RunCreate(BaseModel):
    tool: str
    targets: list[str] = []
    params: dict = {}


@engagement_runs_router.post("/{engagement_id}/runs", status_code=202)
async def create_run(
    engagement_id: UUID,
    body: RunCreate,
    eng: Annotated[Engagement, Depends(require_engagement_access("client_viewer"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Client viewers cannot create runs.
    if not await is_admin(current_user, db):
        member = await db.scalar(
            select(EngagementMember).where(
                EngagementMember.engagement_id == engagement_id,
                EngagementMember.user_id == current_user.id,
            )
        )
        if member is None or member.role == "client_viewer":
            raise HTTPException(status_code=403, detail="Forbidden")

    scope = await db.scalar(select(Scope).where(Scope.engagement_id == eng.id))
    entries = []
    if scope:
        rows = await db.scalars(select(ScopeEntry).where(ScopeEntry.scope_id == scope.id))
        entries = list(rows)
    targets = body.targets or []
    scope_result = check_scope(entries, targets)

    run = Run(
        engagement_id=eng.id,
        user_id=current_user.id,
        tool=body.tool,
        target_ids=[],
        params={**(body.params or {}), "targets": targets},
        status=RunStatus.QUEUED,
        scope_warning=scope_result.has_warning,
    )
    db.add(run)
    await db.flush()
    if scope_result.has_warning:
        await AuditService.log(
            db,
            current_user.id,
            "scope.warning",
            "run",
            run.id,
            eng.id,
            {"out_of_scope": scope_result.out_of_scope, "targets": targets},
        )
    await AuditService.log(
        db, current_user.id, "run.enqueue", "run", run.id, eng.id, {"tool": body.tool}
    )
    await db.commit()
    return {"id": str(run.id), "status": run.status.value}


@runs_router.get("/{run_id}")
async def get_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not await can_access_engagement(current_user, run.engagement_id, db):
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": str(run.id),
        "status": run.status.value,
        "tool": run.tool,
        "scope_warning": run.scope_warning,
    }


@runs_router.get("/{run_id}/logs")
async def get_run_logs(
    run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not await can_access_engagement(current_user, run.engagement_id, db):
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await db.scalars(
        select(Evidence).where(Evidence.run_id == run.id, Evidence.type == "tool_output")
    )
    logs = [{"stdout": r.meta.get("stdout"), "stderr": r.meta.get("stderr")} for r in rows if r.meta]
    return {"run_id": str(run.id), "logs": logs}
