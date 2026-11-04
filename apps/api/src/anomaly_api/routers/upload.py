from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from anomaly_api.deps import CurrentUser

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_file(user: CurrentUser, file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content), "content_type": file.content_type}
