from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from anomaly_core.db import Base

if TYPE_CHECKING:
    from .engagement import Engagement, Target
    from .run import Run
    from .user import User


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class FindingSeverity(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FindingStatus(StrEnum):
    new = "new"
    triaged = "triaged"
    confirmed = "confirmed"
    fixed = "fixed"
    false_positive = "false_positive"


class EvidenceType(StrEnum):
    screenshot = "screenshot"
    request_response = "request_response"
    tool_output = "tool_output"
    log = "log"


class ReportStatus(StrEnum):
    draft = "draft"
    review = "review"
    published = "published"


class ReportFormat(StrEnum):
    markdown = "markdown"
    html = "html"
    pdf = "pdf"


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("targets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    severity: Mapped[FindingSeverity] = mapped_column(
        SAEnum(FindingSeverity, values_callable=_enum_values),
        default=FindingSeverity.medium,
        nullable=False,
        index=True,
    )
    status: Mapped[FindingStatus] = mapped_column(
        SAEnum(FindingStatus, values_callable=_enum_values),
        default=FindingStatus.new,
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    cvss: Mapped[float | None] = mapped_column(Float, nullable=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ai_drafted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    engagement: Mapped[Engagement] = relationship(
        "Engagement", back_populates="findings", lazy="selectin"
    )
    target: Mapped[Target | None] = relationship("Target", lazy="selectin")
    evidence: Mapped[list[Evidence]] = relationship(
        "Evidence", back_populates="finding", cascade="all, delete-orphan", lazy="selectin"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[EvidenceType] = mapped_column(
        SAEnum(EvidenceType, values_callable=_enum_values), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    finding: Mapped[Finding | None] = relationship(
        "Finding", back_populates="evidence", lazy="selectin"
    )
    run: Mapped[Run | None] = relationship("Run", back_populates="evidence", lazy="selectin")


def _evidence_metadata_get(self: Evidence) -> dict[str, Any]:
    return self.metadata_


def _evidence_metadata_set(self: Evidence, value: dict[str, Any]) -> None:
    self.metadata_ = value


Evidence.metadata = property(_evidence_metadata_get, _evidence_metadata_set)  # type: ignore[assignment]


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus, values_callable=_enum_values),
        default=ReportStatus.draft,
        nullable=False,
        index=True,
    )
    format: Mapped[ReportFormat] = mapped_column(
        SAEnum(ReportFormat, values_callable=_enum_values),
        default=ReportFormat.markdown,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    engagement: Mapped[Engagement] = relationship("Engagement", lazy="selectin")
    author: Mapped[User] = relationship("User", foreign_keys=[author_id], lazy="selectin")
    approver: Mapped[User | None] = relationship(
        "User", foreign_keys=[approver_id], lazy="selectin"
    )
