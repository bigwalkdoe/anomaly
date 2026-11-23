"""drop legacy ab12 tenancy artifacts

Revision ID: 0a1b2c3d4e5f
Revises: f2a3b4c5d6e7
Create Date: 2026-11-23 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def _has_index(bind, table: str, name: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(i["name"] == name for i in sa.inspect(bind).get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    # organization_members was a dead-branch artifact from ab12; current code uses memberships.
    if _has_table(bind, "organization_members"):
        for idx in ["ix_organization_members_created_at", "ix_organization_members_role"]:
            if _has_index(bind, "organization_members", idx):
                op.drop_index(idx, table_name="organization_members")
        op.drop_table("organization_members")

    # organizations.status was added by ab12 but is not in the current model.
    if _has_column(bind, "organizations", "status"):
        if _has_index(bind, "organizations", "ix_organizations_status"):
            op.drop_index("ix_organizations_status", table_name="organizations")
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.drop_column("status")

    # Drop dead enum types if present (Postgres only).
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP TYPE IF EXISTS organizationrole"))
        op.execute(sa.text("DROP TYPE IF EXISTS organizationstatus"))


def downgrade() -> None:
    # Non-destructive downgrade: legacy dead-branch artifacts are not restored.
    pass
