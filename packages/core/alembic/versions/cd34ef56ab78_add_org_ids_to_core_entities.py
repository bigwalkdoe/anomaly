"""add organization ids to core entities

Revision ID: cd34ef56ab78
Revises: ab12cd34ef56
Create Date: 2026-11-10 17:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cd34ef56ab78"
down_revision: str | Sequence[str] | None = "ab12cd34ef56"
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


def _add_org_column(table: str, ondelete: str = "CASCADE") -> None:
    bind = op.get_bind()
    if not _has_column(bind, table, "organization_id"):
        op.add_column(table, sa.Column("organization_id", sa.UUID(), nullable=True))
    idx = f"ix_{table}_organization_id"
    if not _has_index(bind, table, idx):
        op.create_index(idx, table, ["organization_id"], unique=False)
    fk = f"fk_{table}_organization_id"
    canonical_fk = f"fk_{table}_organization_id_organizations"
    if not _has_fk(bind, table, fk) and not _has_fk(bind, table, canonical_fk):
        op.create_foreign_key(
            fk, table, "organizations", ["organization_id"], ["id"], ondelete=ondelete
        )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    _add_org_column("runs")
    _add_org_column("findings")
    _add_org_column("evidence")
    _add_org_column("reports")
    _add_org_column("audit_logs", ondelete="SET NULL")
    _add_org_column("approvals")
    if not _has_column(bind, "approvals", "engagement_id"):
        op.add_column("approvals", sa.Column("engagement_id", sa.UUID(), nullable=True))
    if not _has_index(bind, "approvals", "ix_approvals_engagement_id"):
        op.create_index("ix_approvals_engagement_id", "approvals", ["engagement_id"], unique=False)
    if not _has_fk(bind, "approvals", "fk_approvals_engagement_id"):
        op.create_foreign_key(
            "fk_approvals_engagement_id",
            "approvals",
            "engagements",
            ["engagement_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_approvals_engagement_id", "approvals", type_="foreignkey")
    op.drop_index("ix_approvals_engagement_id", table_name="approvals")
    op.drop_column("approvals", "engagement_id")

    for table, fk in [
        ("approvals", "fk_approvals_organization_id"),
        ("audit_logs", "fk_audit_logs_organization_id"),
        ("reports", "fk_reports_organization_id"),
        ("evidence", "fk_evidence_organization_id"),
        ("findings", "fk_findings_organization_id"),
        ("runs", "fk_runs_organization_id"),
    ]:
        op.drop_constraint(fk, table, type_="foreignkey")
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_column(table, "organization_id")
