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
    from .engagement import Engagement
    from .finding import Evidence
    from .user import User


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_ids: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, values_callable=_enum_values),
        default=RunStatus.queued,
        nullable=False,
        index=True,
    )
    scope_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    engagement: Mapped[Engagement] = relationship("Engagement", lazy="selectin")
    user: Mapped[User] = relationship("User", lazy="selectin")
    evidence: Mapped[list[Evidence]] = relationship(
        "Evidence", back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
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

    owner: Mapped[User] = relationship("User", lazy="selectin")
    playbook_steps: Mapped[list[PlaybookStep]] = relationship(
        "PlaybookStep", back_populates="playbook", cascade="all, delete-orphan", lazy="selectin"
    )


class PlaybookStep(Base):
    __tablename__ = "playbook_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playbooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool: Mapped[str] = mapped_column(String(255), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    on_failure: Mapped[str | None] = mapped_column(String(50), nullable=True)
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

    playbook: Mapped[Playbook] = relationship(
        "Playbook", back_populates="playbook_steps", lazy="selectin"
    )
