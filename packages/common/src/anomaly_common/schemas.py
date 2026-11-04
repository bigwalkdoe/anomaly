from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    success: bool = True
    data: Any = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Any = None


class PaginationParams(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
