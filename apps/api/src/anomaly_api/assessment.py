from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.execution import build_execution_manifest
from anomaly_core.models import Engagement, Run, RunStatus, Scope, User
from anomaly_core.policy import evaluate_assessment_request
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def load_engagement_with_scope(db: AsyncSession, engagement_id: UUID) -> Engagement | None:
    try:
        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == engagement_id)
        )
        return res.scalar_one_or_none()
    except Exception:
        return await db.get(Engagement, engagement_id)


async def enforce_assessment_policy(
    db: AsyncSession,
    user: User,
    engagement: Engagement,
    targets: list[str],
    *,
    scope_engagement: Engagement | None = None,
) -> None:
    decision = evaluate_assessment_request(
        engagement, targets, scope_engagement=scope_engagement or engagement
    )
    if decision.allowed:
        return
    await AuditService.log(
        actor_id=getattr(user, "id", None),
        action="policy.denied",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata=decision.metadata,
        db=db,
    )
    await db.commit()
    detail = (
        "Engagement not approved for assessment"
        if decision.reason == "engagement_not_approved"
        else "Requested targets are out of scope"
    )
    raise HTTPException(status_code=403, detail=detail)


async def enqueue_assessment_run(
    db: AsyncSession,
    *,
    user: User,
    engagement: Engagement,
    tool: str,
    targets: list[str],
    params: dict[str, Any] | None = None,
    run_params: dict[str, Any] | None = None,
    manifest_params: dict[str, Any] | None = None,
    enqueue_action: str = "run.enqueue",
    enqueue_metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> Run:
    params = dict(params or {})
    # Ensure scope-checked targets are preserved in stored run params.
    stored_params = dict(run_params if run_params is not None else params)
    stored_params["targets"] = list(targets)

    run = Run(
        organization_id=getattr(engagement, "organization_id", None),
        engagement_id=engagement.id,
        user_id=getattr(user, "id", None),
        tool=tool,
        status=RunStatus.queued,
        scope_warning=False,
        params=stored_params,
    )
    db.add(run)
    await db.flush()

    if manifest_params is None:
        manifest_params = {k: v for k, v in stored_params.items() if k != "targets"}
    manifest = build_execution_manifest(
        run_id=run.id,
        engagement=engagement,
        tool=tool,
        targets=list(targets),
        params=dict(manifest_params),
        policy_decision={"allowed": True, "reason": None},
    )
    run.params = {**stored_params, "execution_manifest": manifest.to_dict()}

    await AuditService.log(
        actor_id=getattr(user, "id", None),
        action=enqueue_action,
        resource_type="run",
        resource_id=run.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={
            "tool": run.tool,
            "targets": list(targets),
            "manifest_ref": str(run.id),
            **(enqueue_metadata or {}),
        },
        db=db,
    )
    if commit:
        await db.commit()
        await db.refresh(run)
    return run


def inline_execution_enabled() -> bool:
    return os.environ.get("RUNNER_MODE") == "inline" or os.environ.get("ANOMALY_INLINE_RUNS") == "1"
