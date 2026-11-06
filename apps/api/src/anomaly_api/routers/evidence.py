from __future__ import annotations

from uuid import UUID

from anomaly_core.models import Evidence
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("")
async def list_evidence(user: CurrentUser, db: DbSession):
    evidence = (await db.scalars(select(Evidence))).all()
    return [
        {
            "id": str(e.id),
            "run_id": str(e.run_id) if e.run_id else None,
            "type": e.type.value,
            "storage_key": e.storage_key,
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
        }
        for e in evidence
    ]


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if evidence is None:
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
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    # In production, this would stream from MinIO
    return {
        "message": "File download would stream from MinIO",
        "storage_key": evidence.storage_key,
    }
