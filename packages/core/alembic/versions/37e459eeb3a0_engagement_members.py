"""engagement_members

Revision ID: 37e459eeb3a0
Revises: bdd80bcd314d
Create Date: 2026-11-04 04:25:03.003957

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37e459eeb3a0"
down_revision: str | Sequence[str] | None = "bdd80bcd314d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "engagement_members",
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role", sa.Enum("admin", "pentester", "client_viewer", name="rolename"), nullable=False
        ),
        sa.PrimaryKeyConstraint("engagement_id", "user_id"),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_engagement_members_engagement_id"),
        "engagement_members",
        ["engagement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_engagement_members_user_id"), "engagement_members", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_engagement_members_user_id"), table_name="engagement_members")
    op.drop_index(op.f("ix_engagement_members_engagement_id"), table_name="engagement_members")
    op.drop_table("engagement_members")
