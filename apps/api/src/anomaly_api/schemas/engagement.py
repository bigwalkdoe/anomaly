from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EngagementCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mode: str = Field(default="own_infra")
    status: str | None = Field(default="draft")
    client_name: str | None = None
    rules_of_engagement: str | None = None
    organization_id: UUID | None = None


class EngagementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    mode: str | None = None
    status: str | None = None
    client_name: str | None = None
    rules_of_engagement: str | None = None


class EngagementResponse(BaseModel):
    id: UUID
    organization_id: UUID | None = None
    name: str
    mode: str
    status: str
    owner_id: UUID
    client_name: str | None = None
    organization_id: UUID | None = None
    workspace_id: UUID | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)
