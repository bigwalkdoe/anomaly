from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import UUID, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from anomaly_core.db import Base
from anomaly_core.models.user import RoleName, _enum_values


class EngagementMember(Base):
    """Assigns a user to an engagement with a role scoped to that engagement."""

    __tablename__ = "engagement_members"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[RoleName] = mapped_column(
        SAEnum(RoleName, values_callable=_enum_values), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
