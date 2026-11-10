from __future__ import annotations

from uuid import UUID

from anomaly_core.models import Engagement, Evidence, Finding, Run
from anomaly_core.rbac import engagement_accessible
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


async def _can_access_evidence(db: DbSession, user, evidence: Evidence) -> bool:
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
        return False
    engagement = await db.get(Engagement, engagement_id)
    if engagement is None:
        return False
    return await engagement_accessible(db, user, engagement)


@router.get("")
async def list_evidence(user: CurrentUser, db: DbSession):
    evidence_rows = (await db.scalars(select(Evidence))).all()
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
    # In production, this would stream from MinIO
    return {
        "message": "File download would stream from MinIO",
        "storage_key": evidence.storage_key,
    }
