from __future__ import annotations

from typing import Annotated
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.models import CronSchedule, Engagement, RoleName
from anomaly_core.scheduler import compute_next_run_at
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(prefix="/api", tags=["schedules"])


class CronScheduleCreate(BaseModel):
    cron_expression: str = Field(..., min_length=1, max_length=100)
    tool: str = Field(..., min_length=1, max_length=255)
    targets: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)
    is_active: bool = Field(default=True)


class CronScheduleResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    cron_expression: str
    tool: str
    targets: list[str]
    params: dict
    is_active: bool
    next_run_at: str | None = None
    last_dispatch_at: str | None = None
    last_dispatch_status: str | None = None
    last_error: str | None = None
    dispatch_count: int = 0

    model_config = ConfigDict(from_attributes=True)


@router.get("/engagements/{engagement_id}/schedules", response_model=list[CronScheduleResponse])
async def list_schedules(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    db: DbSession,
):
    result = await db.execute(
        select(CronSchedule).where(CronSchedule.engagement_id == engagement.id)
    )
    schedules = result.scalars().all()
    return [
        CronScheduleResponse(
            id=s.id,
            engagement_id=s.engagement_id,
            cron_expression=s.cron_expression,
            tool=s.tool,
            targets=s.targets,
            params=s.params,
            is_active=s.is_active,
            next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
            last_dispatch_at=(
                s.last_dispatch_at.isoformat() if s.last_dispatch_at else None
            ),
            last_dispatch_status=s.last_dispatch_status,
            last_error=s.last_error,
            dispatch_count=int(s.dispatch_count or 0),
        )
        for s in schedules
    ]


@router.post(
    "/engagements/{engagement_id}/schedules",
    response_model=CronScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    payload: CronScheduleCreate,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    user: CurrentUser,
    db: DbSession,
):
    next_run_at = None
    if payload.is_active:
        try:
            next_run_at = compute_next_run_at(payload.cron_expression)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid cron_expression") from exc
    schedule = CronSchedule(
        engagement_id=engagement.id,
        cron_expression=payload.cron_expression,
        tool=payload.tool,
        targets=payload.targets,
        params=payload.params,
        is_active=payload.is_active,
        next_run_at=next_run_at,
    )
    db.add(schedule)
    await db.flush()
    await AuditService.log(
        actor_id=user.id,
        action="schedule.create",
        resource_type="schedule",
        resource_id=schedule.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={
            "tool": schedule.tool,
            "cron_expression": schedule.cron_expression,
            "target_count": len(schedule.targets or []),
            "is_active": schedule.is_active,
        },
        db=db,
    )
    await db.commit()
    await db.refresh(schedule)
    return CronScheduleResponse(
        id=schedule.id,
        engagement_id=schedule.engagement_id,
        cron_expression=schedule.cron_expression,
        tool=schedule.tool,
        targets=schedule.targets,
        params=schedule.params,
        is_active=schedule.is_active,
        next_run_at=schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        last_dispatch_at=(
            schedule.last_dispatch_at.isoformat() if schedule.last_dispatch_at else None
        ),
        last_dispatch_status=schedule.last_dispatch_status,
        last_error=schedule.last_error,
        dispatch_count=int(schedule.dispatch_count or 0),
    )


@router.delete(
    "/engagements/{engagement_id}/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_schedule(
    schedule_id: UUID,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(CronSchedule).where(
            CronSchedule.id == schedule_id, CronSchedule.engagement_id == engagement.id
        )
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await AuditService.log(
        actor_id=user.id,
        action="schedule.delete",
        resource_type="schedule",
        resource_id=schedule.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={
            "tool": schedule.tool,
            "cron_expression": schedule.cron_expression,
        },
        db=db,
    )
    await db.delete(schedule)
    await db.commit()
    return None
