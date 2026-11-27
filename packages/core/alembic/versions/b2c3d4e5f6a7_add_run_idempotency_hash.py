"""add assessment idempotency hash to runs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "uq_runs_engagement_user_idempotency"


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def _has_idempotency_constraint(bind) -> bool:
    if not _has_table(bind, "runs"):
        return False
    insp = sa.inspect(bind)
    columns = ["engagement_id", "user_id", "idempotency_key_hash"]
    for uc in insp.get_unique_constraints("runs"):
        if (uc.get("column_names") or []) == columns:
            return True
    for idx in insp.get_indexes("runs"):
        if (idx.get("column_names") or []) == columns and idx.get("unique"):
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "runs"):
        return

    if not _has_column(bind, "runs", "idempotency_key_hash"):
        op.add_column(
            "runs", sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True)
        )

    if not _has_idempotency_constraint(bind):
        op.create_unique_constraint(
            _CONSTRAINT_NAME,
            "runs",
            ["engagement_id", "user_id", "idempotency_key_hash"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "runs"):
        return

    if _has_idempotency_constraint(bind):
        op.drop_constraint(_CONSTRAINT_NAME, "runs", type_="unique")

    if _has_column(bind, "runs", "idempotency_key_hash"):
        op.drop_column("runs", "idempotency_key_hash")
