from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from anomaly_core.db import Base

if TYPE_CHECKING:
    from .finding import Finding
    from .user import User


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class EngagementMode(StrEnum):
    own_infra = "own_infra"
    bug_bounty = "bug_bounty"
    client = "client"


class EngagementStatus(StrEnum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    active = "active"
    paused = "paused"
    closed = "closed"
    completed = "completed"
    archived = "archived"


class TargetType(StrEnum):
    domain = "domain"
    ip = "ip"
    cidr = "cidr"
    url = "url"
    service = "service"


class TargetStatus(StrEnum):
    active = "active"
    discovered = "discovered"
    confirmed = "confirmed"


class ScopeEntryKind(StrEnum):
    in_ = "in"
    out = "out"


class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mode: Mapped[EngagementMode] = mapped_column(
        SAEnum(EngagementMode, values_callable=_enum_values),
        default=EngagementMode.own_infra,
        nullable=False,
    )
    status: Mapped[EngagementStatus] = mapped_column(
        SAEnum(EngagementStatus, values_callable=_enum_values),
        default=EngagementStatus.draft,
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rules_of_engagement: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    approver: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by], lazy="selectin"
    )
    scope: Mapped[Scope | None] = relationship(
        "Scope",
        back_populates="engagement",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    targets: Mapped[list[Target]] = relationship(
        "Target", back_populates="engagement", cascade="all, delete-orphan", lazy="selectin"
    )
    findings: Mapped[list[Finding]] = relationship(
        "Finding", back_populates="engagement", cascade="all, delete-orphan", lazy="selectin"
    )


class Scope(Base):
    __tablename__ = "scopes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        "Engagement", back_populates="scope", lazy="selectin"
    )
    entries: Mapped[list[ScopeEntry]] = relationship(
        "ScopeEntry", back_populates="scope", cascade="all, delete-orphan", lazy="selectin"
    )
    in_scope_targets: Mapped[list[ScopeEntry]] = relationship(
        "ScopeEntry",
        primaryjoin="and_(Scope.id==ScopeEntry.scope_id, ScopeEntry.kind=='in')",
        viewonly=True,
        lazy="selectin",
    )
    out_of_scope_entries: Mapped[list[ScopeEntry]] = relationship(
        "ScopeEntry",
        primaryjoin="and_(Scope.id==ScopeEntry.scope_id, ScopeEntry.kind=='out')",
        viewonly=True,
        lazy="selectin",
    )


class ScopeEntry(Base):
    __tablename__ = "scope_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ScopeEntryKind] = mapped_column(
        SAEnum(ScopeEntryKind, values_callable=_enum_values), nullable=False, index=True
    )
    target_value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
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

    scope: Mapped[Scope] = relationship("Scope", back_populates="entries", lazy="selectin")


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    type: Mapped[TargetType] = mapped_column(
        SAEnum(TargetType, values_callable=_enum_values), nullable=False, index=True
    )
    status: Mapped[TargetStatus] = mapped_column(
        SAEnum(TargetStatus, values_callable=_enum_values),
        default=TargetStatus.active,
        nullable=False,
        index=True,
    )
    discovered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
        "Engagement", back_populates="targets", lazy="selectin"
    )
