from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from anomaly_core.assessment_idempotency import (
    hash_idempotency_key,
    normalize_idempotency_key,
)
from anomaly_core.audit import AuditService
from anomaly_core.execution import build_execution_manifest
from anomaly_core.models import Engagement, Run, RunStatus, Scope, User
from anomaly_core.policy import PolicyDecision, evaluate_assessment_request
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


@dataclass(frozen=True)
class IdempotentRunResult:
    run: Run
    replayed: bool = False


def parse_idempotency_key(raw: str | None) -> str | None:
    key = normalize_idempotency_key(raw)
    return hash_idempotency_key(key) if key is not None else None


async def find_idempotent_run(
    db: AsyncSession,
    *,
    engagement_id: UUID,
    user_id: UUID,
    key_hash: str,
) -> Run | None:
    return await db.scalar(
        select(Run).where(
            Run.engagement_id == engagement_id,
            Run.user_id == user_id,
            Run.idempotency_key_hash == key_hash,
        )
    )


async def record_idempotent_replay(
    db: AsyncSession,
    *,
    user: User,
    engagement: Engagement,
    run: Run,
    key_hash: str,
) -> None:
    await AuditService.log(
        actor_id=getattr(user, "id", None),
        action="run.idempotent_replay",
        resource_type="run",
        resource_id=run.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"idempotency_key_hash": key_hash, "run_id": str(run.id)},
        db=db,
    )
    await db.commit()


async def record_assessment_policy_decision(
    db: AsyncSession,
    user: User,
    engagement: Engagement,
    decision: PolicyDecision,
    *,
    source: str | None,
    op: str = "assessment.request",
) -> None:
    await AuditService.log(
        actor_id=getattr(user, "id", None),
        action="policy.allowed" if decision.allowed else "policy.denied",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata=decision.to_metadata(op=op, source=source),
        db=db,
    )
    await db.commit()


async def enforce_assessment_policy(
    db: AsyncSession,
    user: User,
    engagement: Engagement,
    targets: list[str],
    *,
    scope_engagement: Engagement | None = None,
    source: str | None = None,
) -> PolicyDecision:
    decision = evaluate_assessment_request(
        engagement, targets, scope_engagement=scope_engagement or engagement
    )
    await record_assessment_policy_decision(
        db, user, engagement, decision, source=source
    )
    if decision.allowed:
        return decision
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
    policy_decision: PolicyDecision | None = None,
    idempotency_key_hash: str | None = None,
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
        idempotency_key_hash=idempotency_key_hash,
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
        policy_decision=(policy_decision or PolicyDecision(allowed=True)).to_metadata(),
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


async def enqueue_assessment_run_with_idempotency(
    db: AsyncSession,
    *,
    user: User,
    engagement: Engagement,
    tool: str,
    targets: list[str],
    idempotency_key_hash: str | None,
    policy_decision: PolicyDecision,
    params: dict[str, Any] | None = None,
) -> IdempotentRunResult:
    try:
        run = await enqueue_assessment_run(
            db,
            user=user,
            engagement=engagement,
            tool=tool,
            targets=targets,
            params=params,
            policy_decision=policy_decision,
            idempotency_key_hash=idempotency_key_hash,
            commit=False,
        )
        await db.commit()
        await db.refresh(run)
        return IdempotentRunResult(run=run)
    except IntegrityError:
        await db.rollback()
        if idempotency_key_hash is None:
            raise
        # Rollback expires all ORM instances; reload the ones the replay audit needs.
        await db.refresh(engagement)
        await db.refresh(user)
        existing = await find_idempotent_run(
            db,
            engagement_id=engagement.id,
            user_id=user.id,
            key_hash=idempotency_key_hash,
        )
        if existing is None:
            raise
        await record_idempotent_replay(
            db, user=user, engagement=engagement, run=existing, key_hash=idempotency_key_hash
        )
        return IdempotentRunResult(run=existing, replayed=True)


def inline_execution_enabled() -> bool:
    return os.environ.get("RUNNER_MODE") == "inline" or os.environ.get("ANOMALY_INLINE_RUNS") == "1"
