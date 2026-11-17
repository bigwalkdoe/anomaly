from __future__ import annotations

from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, Evidence, Finding, Run
from anomaly_core.rbac import accessible_engagement_ids, engagement_accessible
from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


async def _resolve_evidence_context(db: DbSession, evidence: Evidence):
    engagement_id = getattr(evidence, "engagement_id", None)
    if engagement_id is None and getattr(evidence, "run_id", None) is not None:
        run = await db.get(Run, evidence.run_id)
        if run is not None:
            engagement_id = run.engagement_id
    if engagement_id is None and getattr(evidence, "finding_id", None) is not None:
        finding = await db.get(Finding, evidence.finding_id)
        if finding is not None:
            engagement_id = finding.engagement_id
    if engagement_id is None:
        return None, None
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        return None, None
    return engagement_id, engagement


async def _can_access_evidence(db: DbSession, user, evidence: Evidence) -> bool:
    _, engagement = await _resolve_evidence_context(db, evidence)
    if engagement is None:
        return False
    return await engagement_accessible(db, user, engagement)


@router.get("")
async def list_evidence(user: CurrentUser, db: DbSession):
    allowed = await accessible_engagement_ids(db, user)
    if allowed is not None and not allowed:
        return []
    stmt = select(Evidence)
    if allowed is not None:
        allowed_list = list(allowed)
        stmt = stmt.where(
            or_(
                Evidence.engagement_id.in_(allowed_list),
                select(Run.id)
                .where(Run.id == Evidence.run_id, Run.engagement_id.in_(allowed_list))
                .exists(),
                select(Finding.id)
                .where(
                    Finding.id == Evidence.finding_id,
                    Finding.engagement_id.in_(allowed_list),
                )
                .exists(),
            )
        )
    evidence_rows = (await db.scalars(stmt)).all()
    items = []
    for e in evidence_rows:
        if not await _can_access_evidence(db, user, e):
            continue
        items.append(
            {
                "id": str(e.id),
                "run_id": str(e.run_id) if e.run_id else None,
                "type": e.type.value,
                "storage_key": e.storage_key,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
        )
    return items


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if evidence is None or not await _can_access_evidence(db, user, evidence):
        raise HTTPException(status_code=404, detail="Evidence not found")
    engagement_id, engagement = await _resolve_evidence_context(db, evidence)
    await AuditService.log(
        actor_id=user.id,
        action="evidence.download",
        resource_type="evidence",
        resource_id=evidence.id,
        engagement_id=engagement_id,
        organization_id=getattr(engagement, "organization_id", None) if engagement else None,
        metadata={"storage_key": evidence.storage_key},
        db=db,
    )
    await db.commit()
    return {
        "id": str(evidence.id),
        "storage_key": evidence.storage_key,
        "type": evidence.type.value,
        "metadata": evidence.metadata,
        "download_url": f"/api/evidence/{evidence_id}/file",
    }


@router.get("/{evidence_id}/file")
async def get_evidence_file(evidence_id: UUID, user: CurrentUser, db: DbSession):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if evidence is None or not await _can_access_evidence(db, user, evidence):
        raise HTTPException(status_code=404, detail="Evidence not found")
    engagement_id, engagement = await _resolve_evidence_context(db, evidence)
    await AuditService.log(
        actor_id=user.id,
        action="evidence.access",
        resource_type="evidence",
        resource_id=evidence.id,
        engagement_id=engagement_id,
        organization_id=getattr(engagement, "organization_id", None) if engagement else None,
        metadata={"storage_key": evidence.storage_key},
        db=db,
    )
    await db.commit()
    # In production, this would stream from MinIO
    return {
        "message": "File download would stream from MinIO",
        "storage_key": evidence.storage_key,
    }


@router.get("/{evidence_id}/integrity")
async def get_evidence_integrity(evidence_id: UUID, user: CurrentUser, db: DbSession):
    import hashlib

    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if evidence is None or not await _can_access_evidence(db, user, evidence):
        raise HTTPException(status_code=404, detail="Evidence not found")
    engagement_id, engagement = await _resolve_evidence_context(db, evidence)
    meta = evidence.metadata or {}
    recorded = evidence.sha256 or meta.get("sha256")

    computed = None
    verification = "unavailable"
    if "stdout" in meta or "stderr" in meta:
        content = f"{meta.get('stdout', '')}\n{meta.get('stderr', '')}".encode(
            "utf-8", errors="replace"
        )
        computed = hashlib.sha256(content).hexdigest()
        if recorded:
            verification = "match" if str(recorded) == computed else "mismatch"
        else:
            verification = "computed"

    return {
        "id": str(evidence.id),
        "sha256": recorded,
        "computed_sha256": computed,
        "recorded": recorded is not None,
        "verified": verification == "match",
        "verification": verification,
        "provenance": {
            "organization_id": str(getattr(engagement, "organization_id", "") or "") or None,
            "engagement_id": str(engagement_id) if engagement_id else None,
            "run_id": str(evidence.run_id) if evidence.run_id else None,
            "finding_id": str(evidence.finding_id) if evidence.finding_id else None,
            "collector": evidence.collector or meta.get("collector"),
            "tool": evidence.tool or meta.get("tool"),
            "storage_key": evidence.storage_key,
        },
        "storage_verification": "inline_content" if computed else "unavailable",
    }
