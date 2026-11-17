from __future__ import annotations

import hashlib
import os
import uuid
from io import BytesIO
from pathlib import PurePosixPath
from typing import Annotated

from anomaly_core.audit import AuditService
from anomaly_core.models import Engagement, Evidence, EvidenceType
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from minio import Minio
from pydantic import BaseModel

from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access

router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))


class UploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    bucket: str
    object_name: str
    url: str


def get_minio_client() -> Minio:
    return Minio(
        os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


@router.post(
    "/engagements/{engagement_id}",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    engagement: Annotated[Engagement, Depends(require_engagement_access("engagement_id"))],
    file: Annotated[UploadFile, File(...)],
    user: CurrentUser,
    db: DbSession,
) -> UploadResponse:
    client = get_minio_client()
    bucket_name = os.environ.get("MINIO_BUCKET", "anomaly-evidence")

    # Ensure bucket exists
    found = client.bucket_exists(bucket_name)
    if not found:
        client.make_bucket(bucket_name)

    raw_name = file.filename or "upload"
    safe_name = PurePosixPath(raw_name).name.replace("\\", "_")
    safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in "._- ") or "upload"
    object_name = f"{uuid.uuid4()}/{safe_name}"
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    client.put_object(
        bucket_name,
        object_name,
        BytesIO(content),
        file_size,
        content_type=file.content_type or "application/octet-stream",
    )

    sha256 = hashlib.sha256(content).hexdigest()

    # Create evidence record with integrity/provenance metadata
    ev = Evidence(
        organization_id=getattr(engagement, "organization_id", None),
        engagement_id=engagement.id,
        run_id=None,
        type=EvidenceType.log,
        storage_key=f"{bucket_name}/{object_name}",
        sha256=sha256,
        collector="upload",
        metadata={
            "filename": safe_name,
            "original_filename": raw_name,
            "size": file_size,
            "content_type": file.content_type,
            "sha256": sha256,
            "collector": "upload",
            "organization_id": str(getattr(engagement, "organization_id", "") or "") or None,
            "engagement_id": str(engagement.id),
        },
    )
    db.add(ev)
    await AuditService.log(
        actor_id=user.id if user else None,
        action="evidence.upload",
        resource_type="evidence",
        resource_id=ev.id,
        engagement_id=engagement.id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"filename": safe_name, "sha256": sha256},
        db=db,
    )
    await db.commit()

    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    return UploadResponse(
        filename=safe_name,
        size=file_size,
        content_type=file.content_type or "application/octet-stream",
        bucket=bucket_name,
        object_name=object_name,
        url=f"http://{endpoint}/{bucket_name}/{object_name}",
    )
