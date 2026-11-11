from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.db import SessionLocal
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementStatus,
    RoleName,
    Run,
    RunStatus,
    Scope,
)
from anomaly_core.scope import check_scope
from anomaly_core.tenancy import get_or_create_default_organization
from anomaly_reporting import ReportGenerator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access
from anomaly_api.routers.auth import me as auth_me
from anomaly_api.schemas.engagement import EngagementCreate, EngagementResponse


def _envelope(request: Request, data: Any) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "meta": {"request_id": getattr(request.state, "request_id", None)},
    }


router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/auth/me")
async def v1_me(request: Request, user: CurrentUser, db: DbSession):
    resp = await auth_me(user=user, db=db)
    return _envelope(request, resp.model_dump(mode="json"))


@router.get("/engagements")
async def v1_list_engagements(
    request: Request, user: CurrentUser, db: DbSession, limit: int = 100, offset: int = 0
):
    # reuse logic similar to legacy
    from anomaly_core.tenancy import get_user_memberships

    memberships = await get_user_memberships(db, user)
    org_ids = {m.organization_id for m in memberships}
    if any(r.name == RoleName.admin for r in user.roles):
        q = select(Engagement)
        if org_ids:
            q = q.where(
                (Engagement.organization_id.in_(org_ids)) | (Engagement.organization_id.is_(None))
            )
        engagements = (await db.scalars(q.offset(offset).limit(limit))).all()
    else:
        members = (
            await db.scalars(select(EngagementMember).where(EngagementMember.user_id == user.id))
        ).all()
        eng_ids = [m.engagement_id for m in members]
        if not eng_ids:
            return _envelope(request, [])
        q = select(Engagement).where(Engagement.id.in_(eng_ids))
        if org_ids:
            q = q.where(
                (Engagement.organization_id.in_(org_ids)) | (Engagement.organization_id.is_(None))
            )
        engagements = (await db.scalars(q.offset(offset).limit(limit))).all()
    return _envelope(
        request, [EngagementResponse.model_validate(e).model_dump(mode="json") for e in engagements]
    )


@router.post("/engagements", status_code=status.HTTP_201_CREATED)
async def v1_create_engagement(
    request: Request, payload: EngagementCreate, user: CurrentUser, db: DbSession
):
    org = await get_or_create_default_organization(db, user)
    from anomaly_core.models import EngagementMode

    engagement = Engagement(
        name=payload.name,
        mode=EngagementMode(payload.mode),
        owner_id=user.id,
        organization_id=org.id,
    )
    db.add(engagement)
    await db.flush()
    scope = Scope(engagement_id=engagement.id)
    db.add(scope)
    db.add(EngagementMember(engagement_id=engagement.id, user_id=user.id, role=RoleName.admin))
    await AuditService.log(
        actor_id=user.id,
        action="engagement.create",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=org.id,
        metadata={"name": engagement.name, "organization_id": str(org.id)},
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return _envelope(request, EngagementResponse.model_validate(engagement).model_dump(mode="json"))


@router.post("/engagements/{engagement_id}/approve")
async def v1_approve_engagement(
    request: Request,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.admin))
    ],
    user: CurrentUser,
    db: DbSession,
):
    from datetime import UTC, datetime

    if engagement.status not in (
        EngagementStatus.pending_approval,
        EngagementStatus.draft,
        EngagementStatus.approved,
    ):
        raise HTTPException(status_code=409, detail="Engagement not in approvable state")
    engagement.status = EngagementStatus.approved
    engagement.approved_by = user.id
    engagement.approved_at = datetime.now(UTC)
    await AuditService.log(
        actor_id=user.id,
        action="engagement.approve",
        resource_type="engagement",
        resource_id=engagement.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"approver_id": str(user.id), "status": engagement.status.value},
        db=db,
    )
    await db.commit()
    await db.refresh(engagement)
    return _envelope(request, EngagementResponse.model_validate(engagement).model_dump(mode="json"))


class V1RunCreate(BaseModel):
    tool: str = "stub"
    targets: list[str] = []
    params: dict = {}


@router.post("/engagements/{engagement_id}/runs", status_code=status.HTTP_202_ACCEPTED)
async def v1_create_run(
    request: Request,
    engagement: Annotated[
        Engagement, Depends(require_engagement_access("engagement_id", min_role=RoleName.pentester))
    ],
    payload: V1RunCreate,
    user: CurrentUser,
    db: DbSession,
):
    # Policy gate (same as legacy)
    if getattr(engagement, "status", None) is not None:
        status_val = (
            engagement.status.value
            if hasattr(engagement.status, "value")
            else str(engagement.status)
        )
        if status_val not in ("approved", "active"):
            await AuditService.log(
                actor_id=user.id,
                action="policy.denied",
                resource_type="engagement",
                resource_id=engagement.id,
                engagement_id=engagement.id,
                organization_id=getattr(engagement, "organization_id", None),
                metadata={
                    "reason": "engagement_not_approved",
                    "status": status_val,
                    "op": "assessment.request",
                },
                db=db,
            )
            await db.commit()
            raise HTTPException(status_code=403, detail="Engagement not approved for assessment")

    targets = payload.targets
    try:
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
    run_params["targets"] = targets
    if result.has_warning and result.out_of_scope:
        await AuditService.log(
            actor_id=user.id,
            action="policy.denied",
            resource_type="engagement",
            resource_id=engagement.id,
            engagement_id=engagement.id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={
                "reason": "out_of_scope",
                "targets": targets,
                "out_of_scope": result.out_of_scope,
            },
            db=db,
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="Requested targets are out of scope")

    run = Run(
        organization_id=getattr(engagement, "organization_id", None),
        engagement_id=engagement.id,
        user_id=user.id,
        tool=payload.tool,
        status=RunStatus.queued,
        scope_warning=False,
        params=run_params,
    )
    db.add(run)
    await db.flush()
    await AuditService.log(
        actor_id=user.id,
        action="run.enqueue",
        resource_type="run",
        resource_id=run.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"tool": run.tool, "targets": targets},
        db=db,
    )
    await db.commit()
    await db.refresh(run)

    import os

    if os.environ.get("RUNNER_MODE") == "inline" or os.environ.get("ANOMALY_INLINE_RUNS") == "1":
        try:
            from anomaly_worker.executor import execute_run

            async with SessionLocal() as db2:
                await execute_run(db2, run.id)
            await db.refresh(run)
        except Exception:
            pass

    return _envelope(
        request, {"id": str(run.id), "status": run.status.value, "scope_warning": run.scope_warning}
    )


@router.get("/runs/{run_id}")
async def v1_get_run(request: Request, run_id: UUID, user: CurrentUser, db: DbSession):
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    engagement = await db.get(Engagement, run.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail="Run not found")
    from anomaly_core.rbac import engagement_accessible

    if not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Run not found")
    return _envelope(
        request, {"id": str(run.id), "status": run.status.value, "scope_warning": run.scope_warning}
    )


@router.get("/engagements/{engagement_id}/reports/generate")
async def v1_generate_report(
    request: Request,
    engagement_id: UUID,
    user: CurrentUser,
    db: DbSession,
    format: str = "markdown",
):
    from anomaly_core.models import Evidence, Finding
    from anomaly_core.rbac import engagement_accessible

    engagement = await db.get(Engagement, engagement_id)
    if engagement is None or not await engagement_accessible(db, user, engagement):
        raise HTTPException(status_code=404, detail="Engagement not found")
    findings = (
        await db.scalars(select(Finding).where(Finding.engagement_id == engagement_id))
    ).all()
    runs = (await db.scalars(select(Run).where(Run.engagement_id == engagement_id))).all()
    evidence_rows = (
        await db.scalars(select(Evidence).where(Evidence.engagement_id == engagement_id))
    ).all()
    if not evidence_rows and runs:
        run_ids = [r.id for r in runs]
        evidence_rows = (
            (await db.scalars(select(Evidence).where(Evidence.run_id.in_(run_ids)))).all()
            if run_ids
            else []
        )
    findings_data = [
        {
            "title": f.title,
            "severity": f.severity.value,
            "description": f.description,
            "status": f.status.value,
            "remediation": f.remediation or "",
        }
        for f in findings
    ]
    run_ids_str = [str(r.id) for r in runs]
    ev_ids = [str(e.id) for e in evidence_rows]
    ev_shas = [e.sha256 or (e.metadata or {}).get("sha256") for e in evidence_rows]
    ev_shas = [s for s in ev_shas if s]
    context = {
        "organization_id": str(getattr(engagement, "organization_id", "") or ""),
        "engagement_id": str(engagement_id),
        "job_id": run_ids_str[0] if run_ids_str else None,
        "run_id": run_ids_str[0] if run_ids_str else None,
        "execution_id": run_ids_str[0] if run_ids_str else None,
        "evidence_ids": ev_ids,
        "evidence_sha256": ev_shas,
    }
    gen = ReportGenerator()
    content: str | bytes
    if format == "html":
        content = gen.generate_html(engagement.name, findings_data, context=context)
    elif format == "pdf":
        content = gen.generate_pdf(engagement.name, findings_data, context=context)
    else:
        content = gen.generate_markdown(engagement.name, findings_data, context=context)
    data = {
        "engagement_id": str(engagement_id),
        "engagement_name": engagement.name,
        "format": format,
        "content": content.decode("utf-8") if isinstance(content, bytes) else content,
        "finding_count": len(findings_data),
        "traceability": context,
    }
    return _envelope(request, data)
