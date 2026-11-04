from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

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


@router.get("/api/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
