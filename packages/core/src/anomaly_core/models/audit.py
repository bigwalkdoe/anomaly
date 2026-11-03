from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from anomaly_core.db import Base

if TYPE_CHECKING:
    from .engagement import Engagement
    from .user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    actor: Mapped[User | None] = relationship("User", lazy="selectin")
    engagement: Mapped[Engagement | None] = relationship("Engagement", lazy="selectin")


def _audit_metadata_get(self: AuditLog) -> dict[str, Any]:
    return self.metadata_


def _audit_metadata_set(self: AuditLog, value: dict[str, Any]) -> None:
    self.metadata_ = value


AuditLog.metadata = property(_audit_metadata_get, _audit_metadata_set)  # type: ignore[assignment]
