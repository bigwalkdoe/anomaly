from pydantic import BaseModel


class FindingCreate(BaseModel):
    title: str
    severity: str
    description: str | None = None
    remediation: str | None = None
    target_id: str | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    severity: str | None = None
    description: str | None = None
    remediation: str | None = None
    status: str | None = None


class FindingStatusUpdate(BaseModel):
    status: str


class FindingOut(BaseModel):
    id: str
    engagement_id: str
    title: str
    severity: str
    status: str
    description: str | None = None
