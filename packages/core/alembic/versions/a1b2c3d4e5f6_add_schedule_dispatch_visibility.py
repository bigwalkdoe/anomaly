"""add schedule dispatch visibility fields

Revision ID: a1b2c3d4e5f6
Revises: 0a1b2c3d4e5f
Create Date: 2026-11-23 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "0a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "cron_schedules"):
        return
    if not _has_column(bind, "cron_schedules", "last_dispatch_at"):
        op.add_column(
            "cron_schedules",
            sa.Column("last_dispatch_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column(bind, "cron_schedules", "last_dispatch_status"):
        op.add_column(
            "cron_schedules",
            sa.Column("last_dispatch_status", sa.String(length=32), nullable=True),
        )
    if not _has_column(bind, "cron_schedules", "last_error"):
        op.add_column(
            "cron_schedules",
            sa.Column("last_error", sa.String(length=1024), nullable=True),
        )
    if not _has_column(bind, "cron_schedules", "dispatch_count"):
        op.add_column(
            "cron_schedules",
            sa.Column("dispatch_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("cron_schedules", "dispatch_count", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "cron_schedules"):
        return
    for col in ["dispatch_count", "last_error", "last_dispatch_status", "last_dispatch_at"]:
        if _has_column(bind, "cron_schedules", col):
            op.drop_column("cron_schedules", col)
