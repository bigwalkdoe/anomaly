"""add organization scope to tags

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-23 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "e1f2a3b4c5d6"
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


def _has_fk(bind, table: str, name: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(fk.get("name") == name for fk in sa.inspect(bind).get_foreign_keys(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "tags"):
        return

    if not _has_column(bind, "tags", "organization_id"):
        op.add_column("tags", sa.Column("organization_id", sa.UUID(), nullable=True))

    # Drop legacy global unique on name if present (name varies by dialect/naming).
    insp = sa.inspect(bind)
    for uc in insp.get_unique_constraints("tags"):
        cols = uc.get("column_names") or []
        if cols == ["name"] and uc.get("name"):
            op.drop_constraint(uc["name"], "tags", type_="unique")
    for idx in insp.get_indexes("tags"):
        cols = idx.get("column_names") or []
        if cols == ["name"] and idx.get("unique"):
            op.drop_index(idx["name"], table_name="tags")

    if not _has_index(bind, "tags", "ix_tags_organization_id"):
        op.create_index("ix_tags_organization_id", "tags", ["organization_id"], unique=False)
    if not _has_fk(bind, "tags", "fk_tags_organization_id"):
        op.create_foreign_key(
            "fk_tags_organization_id",
            "tags",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

    insp = sa.inspect(bind)
    has_org_name_uq = any(
        (uc.get("column_names") or []) == ["organization_id", "name"]
        for uc in insp.get_unique_constraints("tags")
    )
    has_org_name_idx = any(
        (idx.get("column_names") or []) == ["organization_id", "name"] and idx.get("unique")
        for idx in insp.get_indexes("tags")
    )
    if not has_org_name_uq and not has_org_name_idx:
        op.create_unique_constraint("uq_tags_org_name", "tags", ["organization_id", "name"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "tags"):
        return
    if _has_fk(bind, "tags", "fk_tags_organization_id"):
        op.drop_constraint("fk_tags_organization_id", "tags", type_="foreignkey")
    insp = sa.inspect(bind)
    for uc in insp.get_unique_constraints("tags"):
        if (uc.get("column_names") or []) == ["organization_id", "name"] and uc.get("name"):
            op.drop_constraint(uc["name"], "tags", type_="unique")
    if _has_index(bind, "tags", "ix_tags_organization_id"):
        op.drop_index("ix_tags_organization_id", table_name="tags")
    if _has_column(bind, "tags", "organization_id"):
        op.drop_column("tags", "organization_id")
    # Legacy global unique on name is not restored.
