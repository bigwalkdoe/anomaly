from __future__ import annotations

import os
from typing import Annotated

from anomaly_core.models import RoleName, User
from anomaly_core.rbac import has_role
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from anomaly_api.deps import get_optional_user

router = APIRouter(tags=["metrics"])

REQUEST_COUNT = Counter(
    "anomaly_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "anomaly_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
)


def _metrics_auth_required() -> bool:
    v = os.getenv("ANOMALY_METRICS_AUTH_REQUIRED", "")
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


@router.get("/api/metrics")
async def metrics(user: Annotated[User | None, Depends(get_optional_user)]):
    if _metrics_auth_required():
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if not has_role(user, RoleName.admin):
            raise HTTPException(status_code=403, detail="Forbidden")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
