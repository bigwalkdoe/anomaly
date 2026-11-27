from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from croniter import croniter  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from anomaly_core.audit import AuditService
from anomaly_core.execution import build_execution_manifest
from anomaly_core.models import CronSchedule, Engagement, Run, RunStatus, Scope, User
from anomaly_core.policy import PolicyDecision, evaluate_assessment_request


@dataclass
class ScheduleDispatchResult:
    schedule_id: UUID
    status: str  # dispatched | skipped | failed
    run_id: UUID | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def compute_next_run_at(cron_expression: str, *, base: datetime | None = None) -> datetime:
    base = base or datetime.now(UTC)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    itr = croniter(cron_expression, base)
    nxt = itr.get_next(datetime)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=UTC)
    return nxt


async def _load_schedule_context(
    db: AsyncSession, schedule: CronSchedule
) -> tuple[Engagement | None, User | None]:
    res = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scope).selectinload(Scope.entries))
        .where(Engagement.id == schedule.engagement_id)
    )
    engagement = res.scalar_one_or_none()
    actor: User | None = None
    if engagement is not None and getattr(engagement, "owner_id", None):
        actor = await db.get(User, engagement.owner_id)
    return engagement, actor


async def _enqueue_scheduled_run(
    db: AsyncSession,
    *,
    actor: User,
    engagement: Engagement,
    schedule: CronSchedule,
    targets: list[str],
    params: dict[str, Any],
    policy_decision: PolicyDecision,
) -> Run:
    stored_params = dict(params)
    stored_params["targets"] = list(targets)
    run = Run(
        organization_id=getattr(engagement, "organization_id", None),
        engagement_id=engagement.id,
        user_id=getattr(actor, "id", None),
        tool=schedule.tool,
        status=RunStatus.queued,
        scope_warning=False,
        params=stored_params,
    )
    db.add(run)
    await db.flush()

    manifest_params = {k: v for k, v in stored_params.items() if k != "targets"}
    manifest = build_execution_manifest(
        run_id=run.id,
        engagement=engagement,
        tool=schedule.tool,
        targets=list(targets),
        params=dict(manifest_params),
        policy_decision=policy_decision.to_metadata(source="schedule"),
    )
    run.params = {**stored_params, "execution_manifest": manifest.to_dict()}

    await AuditService.log(
        actor_id=getattr(actor, "id", None),
        action="run.enqueue",
        resource_type="run",
        resource_id=run.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={
            "tool": run.tool,
            "targets": list(targets),
            "manifest_ref": str(run.id),
            "source": "schedule",
            "schedule_id": str(schedule.id),
            "cron_expression": schedule.cron_expression,
        },
        db=db,
    )
    return run


async def dispatch_due_schedules(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> list[ScheduleDispatchResult]:
    """Dispatch due active schedules through the shared assessment enqueue flow.

    For each due schedule: validate engagement/policy, enqueue a run with an
    execution manifest, audit the enqueue, and advance next_run_at. Policy and
    execution-manifest re-validation is still enforced by the worker executor
    before execution.
    """
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    rows = (
        await db.scalars(
            select(CronSchedule)
            .where(CronSchedule.is_active.is_(True))
            .order_by(CronSchedule.next_run_at.asc().nullsfirst(), CronSchedule.created_at.asc())
            .limit(limit)
        )
    ).all()

    results: list[ScheduleDispatchResult] = []
    for schedule in rows:
        try:
            if schedule.next_run_at is None:
                schedule.next_run_at = compute_next_run_at(schedule.cron_expression, base=now)
                schedule.last_dispatch_at = now
                schedule.last_dispatch_status = "initialized"
                schedule.last_error = None
                await db.commit()
                if schedule.next_run_at > now:
                    results.append(
                        ScheduleDispatchResult(
                            schedule_id=schedule.id,
                            status="skipped",
                            reason="next_run_initialized",
                            metadata={"next_run_at": schedule.next_run_at.isoformat()},
                        )
                    )
                    continue

            if schedule.next_run_at is not None and schedule.next_run_at > now:
                continue

            engagement, actor = await _load_schedule_context(db, schedule)
            if engagement is None:
                schedule.is_active = False
                schedule.last_dispatch_at = now
                schedule.last_dispatch_status = "failed"
                schedule.last_error = "engagement_not_found"
                schedule.dispatch_count = int(schedule.dispatch_count or 0) + 1
                await AuditService.log(
                    actor_id=getattr(actor, "id", None),
                    action="schedule.dispatch_failed",
                    resource_type="schedule",
                    resource_id=schedule.id,
                    engagement_id=schedule.engagement_id,
                    metadata={"reason": "engagement_not_found"},
                    db=db,
                )
                await db.commit()
                results.append(
                    ScheduleDispatchResult(
                        schedule_id=schedule.id,
                        status="failed",
                        reason="engagement_not_found",
                    )
                )
                continue

            if actor is None:
                schedule.is_active = False
                schedule.last_dispatch_at = now
                schedule.last_dispatch_status = "failed"
                schedule.last_error = "owner_not_found"
                schedule.dispatch_count = int(schedule.dispatch_count or 0) + 1
                await AuditService.log(
                    actor_id=None,
                    action="schedule.dispatch_failed",
                    resource_type="schedule",
                    resource_id=schedule.id,
                    engagement_id=engagement.id,
                    organization_id=getattr(engagement, "organization_id", None),
                    metadata={"reason": "owner_not_found"},
                    db=db,
                )
                await db.commit()
                results.append(
                    ScheduleDispatchResult(
                        schedule_id=schedule.id,
                        status="failed",
                        reason="owner_not_found",
                    )
                )
                continue

            targets = [str(t) for t in (schedule.targets or []) if str(t)]
            params = dict(schedule.params or {})

            decision = evaluate_assessment_request(
                engagement, targets, scope_engagement=engagement
            )
            if not decision.allowed:
                await AuditService.log(
                    actor_id=actor.id,
                    action="policy.denied",
                    resource_type="engagement",
                    resource_id=engagement.id,
                    engagement_id=engagement.id,
                    organization_id=getattr(engagement, "organization_id", None),
                    metadata=decision.to_metadata(source="schedule"),
                    db=db,
                )
                schedule.next_run_at = compute_next_run_at(schedule.cron_expression, base=now)
                schedule.last_dispatch_at = now
                schedule.last_dispatch_status = "denied"
                schedule.last_error = decision.reason
                schedule.dispatch_count = int(schedule.dispatch_count or 0) + 1
                await AuditService.log(
                    actor_id=actor.id,
                    action="schedule.dispatch_denied",
                    resource_type="schedule",
                    resource_id=schedule.id,
                    engagement_id=engagement.id,
                    organization_id=getattr(engagement, "organization_id", None),
                    metadata={
                        "reason": decision.reason,
                        "next_run_at": schedule.next_run_at.isoformat(),
                    },
                    db=db,
                )
                await db.commit()
                results.append(
                    ScheduleDispatchResult(
                        schedule_id=schedule.id,
                        status="skipped",
                        reason="policy_denied",
                        metadata={"next_run_at": schedule.next_run_at.isoformat()},
                    )
                )
                continue

            run = await _enqueue_scheduled_run(
                db,
                actor=actor,
                engagement=engagement,
                schedule=schedule,
                targets=targets,
                params=params,
                policy_decision=decision,
            )

            schedule.next_run_at = compute_next_run_at(schedule.cron_expression, base=now)
            schedule.last_dispatch_at = now
            schedule.last_dispatch_status = "dispatched"
            schedule.last_error = None
            schedule.dispatch_count = int(schedule.dispatch_count or 0) + 1
            await AuditService.log(
                actor_id=actor.id,
                action="schedule.dispatch",
                resource_type="schedule",
                resource_id=schedule.id,
                engagement_id=engagement.id,
                organization_id=getattr(engagement, "organization_id", None),
                metadata={
                    "run_id": str(run.id),
                    "tool": schedule.tool,
                    "target_count": len(targets),
                    "next_run_at": schedule.next_run_at.isoformat(),
                },
                db=db,
            )
            await db.commit()
            results.append(
                ScheduleDispatchResult(
                    schedule_id=schedule.id,
                    status="dispatched",
                    run_id=run.id,
                    metadata={"next_run_at": schedule.next_run_at.isoformat()},
                )
            )
        except Exception as exc:
            await db.rollback()
            reason = f"error:{exc.__class__.__name__}"
            try:
                fresh = await db.get(CronSchedule, schedule.id)
                if fresh is not None:
                    fresh.last_dispatch_at = now
                    fresh.last_dispatch_status = "failed"
                    fresh.last_error = reason[:1024]
                    fresh.dispatch_count = int(fresh.dispatch_count or 0) + 1
                    await db.commit()
            except Exception:
                await db.rollback()
            results.append(
                ScheduleDispatchResult(
                    schedule_id=schedule.id,
                    status="failed",
                    reason=reason,
                )
            )

    return results
