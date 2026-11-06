from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

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
