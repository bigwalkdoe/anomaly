from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response - either tokens (no MFA) or mfa_required (MFA needed)."""

    mfa_required: bool = False
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = "bearer"
    user_id: str | None = None


class MembershipResponse(BaseModel):
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    role: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    roles: list[str] = Field(default_factory=list)
    memberships: list[MembershipResponse] = Field(default_factory=list)
    organizations: list[uuid.UUID] = Field(default_factory=list)
