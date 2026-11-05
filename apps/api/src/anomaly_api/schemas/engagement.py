from pydantic import BaseModel


class EngagementCreate(BaseModel):
    name: str
    mode: str
    client_name: str | None = None
    rules_of_engagement: str | None = None


class EngagementUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    client_name: str | None = None
    rules_of_engagement: str | None = None


class EngagementOut(BaseModel):
    id: str
    name: str
    mode: str
    status: str
    client_name: str | None = None


class ScopePut(BaseModel):
    notes: str | None = None
    in_scope: list[str] = []
    out_of_scope: list[str] = []


class ScopeOut(BaseModel):
    notes: str | None = None
    in_scope: list[str] = []
    out_of_scope: list[str] = []


class TargetCreate(BaseModel):
    value: str
    type: str
    status: str = "active"
    discovered: bool = False
