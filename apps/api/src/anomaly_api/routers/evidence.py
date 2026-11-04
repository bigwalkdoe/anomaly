from __future__ import annotations

from anomaly_core.models import Evidence
from fastapi import APIRouter
from sqlalchemy import select

from anomaly_api.deps import CurrentUser, DbSession

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("")
async def list_evidence(user: CurrentUser, db: DbSession):
    evidence = (await db.scalars(select(Evidence))).all()
    return [
        {
            "id": str(e.id),
            "run_id": str(e.run_id),
            "type": e.type.value,
            "storage_key": e.storage_key,
        }
        for e in evidence
    ]
