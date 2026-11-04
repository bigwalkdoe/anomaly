from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, Playbook, PlaybookStep, Run, RunStatus
from anomaly_core.rbac import engagement_accessible
from anomaly_core.runner import FakeRunner, RunSpec
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(prefix="/api", tags=["playbooks"])


class PlaybookStepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tool: str = Field(..., min_length=1, max_length=255)
    params: dict = Field(default_factory=dict)
    order: int = Field(default=0)


class PlaybookStepResponse(BaseModel):
    id: UUID
    playbook_id: UUID
    name: str
    description: Optional[str] = None
    tool: str
    params: dict
    order: int

    class Config:
        from_attributes = True


class PlaybookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    steps: list[PlaybookStepCreate] = Field(default_factory=list)


class PlaybookUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class PlaybookResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    name: str
    description: Optional[str] = None
    steps: list[PlaybookStepResponse] = []

    class Config:
        from_attributes = True


class PlaybookExecuteResponse(BaseModel):
    playbook_id: UUID
    status: str
    runs_created: int
    message: str


@router.get("/engagements/{engagement_id}/playbooks", response_model=list[PlaybookResponse])
async def list_playbooks(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    db: DbSession,
):
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.steps))
        .where(Playbook.engagement_id == engagement.id)
    )
    playbooks = result.scalars().all()
    return [PlaybookResponse.model_validate(p) for p in playbooks]


@router.post("/engagements/{engagement_id}/playbooks", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    engagement_id: UUID,
    payload: PlaybookCreate,
    user: CurrentUser,
    db: DbSession,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Forbidden")
    playbook = Playbook(
        engagement_id=engagement_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(playbook)
    await db.flush()
    for step_data in payload.steps:
        step = PlaybookStep(
            playbook_id=playbook.id,
            name=step_data.name,
            description=step_data.description,
            tool=step_data.tool,
            params=step_data.params,
            order=step_data.order,
        )
        db.add(step)
    await db.commit()
    await db.refresh(playbook)
    result = await db.execute(
        select(Playbook).options(selectinload(Playbook.steps)).where(Playbook.id == playbook.id)
    )
    playbook = result.scalar_one()
    return PlaybookResponse.model_validate(playbook)


@router.get("/engagements/{engagement_id}/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    engagement_id: UUID,
    playbook_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Forbidden")
    result = await db.execute(
        select(Playbook).options(selectinload(Playbook.steps)).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return PlaybookResponse.model_validate(playbook)


@router.patch("/engagements/{engagement_id}/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    engagement_id: UUID,
    playbook_id: UUID,
    payload: PlaybookUpdate,
    user: CurrentUser,
    db: DbSession,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Forbidden")
    result = await db.execute(
        select(Playbook).options(selectinload(Playbook.steps)).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        playbook.name = update_data["name"]
    if "description" in update_data:
        playbook.description = update_data["description"]
    await db.commit()
    await db.refresh(playbook)
    return PlaybookResponse.model_validate(playbook)


@router.delete("/engagements/{engagement_id}/playbooks/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    engagement_id: UUID,
    playbook_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Forbidden")
    result = await db.execute(select(Playbook).where(Playbook.id == playbook_id))
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    await db.delete(playbook)
    await db.commit()
    return None


@router.post("/engagements/{engagement_id}/playbooks/{playbook_id}/execute", response_model=PlaybookExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_playbook(
    engagement_id: UUID,
    playbook_id: UUID,
    payload: dict,
    user: CurrentUser,
    db: DbSession,
):
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Forbidden")
    result = await db.execute(
        select(Playbook).options(selectinload(Playbook.steps)).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    targets = payload.get("targets", [])
    runs_created = 0
    runner = FakeRunner()
    run_ids = []
    for step in sorted(playbook.steps, key=lambda s: s.order):
        run = Run(
            engagement_id=engagement_id,
            user_id=user.id,
            tool=step.tool,
            status=RunStatus.queued,
            scope_warning=False,
            params={
                "playbook_id": str(playbook.id),
                "step_id": str(step.id),
                "step_name": step.name,
                "params": step.params,
            },
        )
        db.add(run)
        await db.flush()
        run_ids.append(run.id)
        runs_created += 1
        await AuditService.log(
            actor_id=user.id,
            action="playbook.step.run",
            resource_type="run",
            resource_id=run.id,
            engagement_id=engagement_id,
            metadata={
                "playbook_id": str(playbook.id),
                "step_id": str(step.id),
                "tool": step.tool,
                "targets": targets,
            },
            db=db,
        )
    await db.commit()

    # Execute runs inline if configured
    import os

    if os.environ.get("RUNNER_MODE") == "inline" or os.environ.get("ANOMALY_INLINE_RUNS") == "1":
        from anomaly_worker.executor import execute_run

        async with SessionLocal() as db2:
            for rid in run_ids:
                try:
                    await execute_run(db2, rid, runner)
                except Exception:
                    pass

    return PlaybookExecuteResponse(
        playbook_id=playbook_id,
        status="queued",
        runs_created=runs_created,
        message=f"Playbook '{playbook.name}' executed with {runs_created} runs",
    )
