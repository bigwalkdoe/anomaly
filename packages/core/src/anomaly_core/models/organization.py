from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from anomaly_core.db import Base

if TYPE_CHECKING:
    from .user import User


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class OrganizationStatus(StrEnum):
    active = "active"
    disabled = "disabled"


class OrganizationRole(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        SAEnum(OrganizationStatus, values_callable=_enum_values),
        default=OrganizationStatus.active,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    memberships: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[OrganizationRole] = mapped_column(
        SAEnum(OrganizationRole, values_callable=_enum_values),
        default=OrganizationRole.member,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="memberships", lazy="selectin"
    )
    user: Mapped[User] = relationship("User", lazy="selectin")
