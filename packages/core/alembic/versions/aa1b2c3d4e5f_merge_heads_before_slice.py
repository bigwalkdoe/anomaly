"""merge heads before tenancy/slice migrations

Revision ID: aa1b2c3d4e5f
Revises: f6b770b737bd
Create Date: 2026-11-10 14:00:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "aa1b2c3d4e5f"
# b07b80459ce9 (engagement_members, removed duplicate chain) was previously merged here;
# the surviving engagement_members migration is 37e459eeb3a0 on the f6b770b737bd line.
down_revision: str | Sequence[str] | None = "f6b770b737bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge heads."""
    pass


def downgrade() -> None:
    """Unmerge heads."""
    pass
