from __future__ import annotations

from anomaly_common import BaseResponse, ErrorResponse, PaginationParams, generate_id, utc_now


def test_schemas():
    assert BaseResponse().success is True
    assert ErrorResponse(error="bad").success is False
    p = PaginationParams(limit=10)
    assert p.offset == 0


def test_utils():
    assert utc_now().tzinfo is not None
    assert len(generate_id()) == 36
