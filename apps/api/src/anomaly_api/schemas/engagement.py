from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class EngagementCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mode: str = Field(default="own_infra")
    status: Optional[str] = Field(default="draft")
    client_name: Optional[str] = None
    rules_of_engagement: Optional[str] = None


class EngagementUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    mode: Optional[str] = None
    status: Optional[str] = None
    client_name: Optional[str] = None
    rules_of_engagement: Optional[str] = None


class EngagementResponse(BaseModel):
    id: UUID
    name: str
    mode: str
    status: str
    owner_id: UUID
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


class ScopeEntryCreate(BaseModel):
    kind: str  # "in" or "out"
    target_value: str = Field(..., min_length=1, max_length=500)


class ScopeUpdate(BaseModel):
    entries: list[ScopeEntryCreate]


class TargetCreate(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)
    type: str = Field(default="domain")


class TargetResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    value: str
    type: str

    class Config:
        from_attributes = True
