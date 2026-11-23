"""merge tenancy heads and reconcile canonical schema

Revision ID: e1f2a3b4c5d6
Revises: bb2c3d4e5f60, cd34ef56ab78
Create Date: 2026-11-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = ("bb2c3d4e5f60", "cd34ef56ab78")
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
    """Reconcile to canonical tenancy/evidence schema expected by current models."""
    bind = op.get_bind()

    # Canonical organizations table (bb shape) - do not destroy ab-only columns if present.
    if not _has_table(bind, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
    if not _has_index(bind, "organizations", "ix_organizations_created_at"):
        op.create_index(
            "ix_organizations_created_at", "organizations", ["created_at"], unique=False
        )
    if not _has_index(bind, "organizations", "ix_organizations_slug"):
        op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    # ab12 branch created organizations.status NOT NULL; current model does not use it.
    if _has_column(bind, "organizations", "status"):
        op.alter_column("organizations", "status", nullable=True)

    if not _has_table(bind, "workspaces"):
        op.create_table(
            "workspaces",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
        )
    for idx, cols in [
        ("ix_workspaces_created_at", ["created_at"]),
        ("ix_workspaces_organization_id", ["organization_id"]),
        ("ix_workspaces_slug", ["slug"]),
    ]:
        if not _has_index(bind, "workspaces", idx):
            op.create_index(idx, "workspaces", cols, unique=False)

    if not _has_table(bind, "memberships"):
        op.create_table(
            "memberships",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=False),
            sa.Column("workspace_id", sa.UUID(), nullable=True),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "organization_id", "workspace_id", name="uq_membership_user_org_ws"
            ),
        )
    for idx, cols in [
        ("ix_memberships_created_at", ["created_at"]),
        ("ix_memberships_organization_id", ["organization_id"]),
        ("ix_memberships_role", ["role"]),
        ("ix_memberships_user_id", ["user_id"]),
        ("ix_memberships_workspace_id", ["workspace_id"]),
    ]:
        if not _has_index(bind, "memberships", idx):
            op.create_index(idx, "memberships", cols, unique=False)

    # Engagement canonical columns
    for col, coltype in [
        ("organization_id", sa.UUID()),
        ("workspace_id", sa.UUID()),
        ("approved_by", sa.UUID()),
        ("approved_at", sa.DateTime(timezone=True)),
    ]:
        if not _has_column(bind, "engagements", col):
            op.add_column("engagements", sa.Column(col, coltype, nullable=True))
    for idx, cols in [
        ("ix_engagements_organization_id", ["organization_id"]),
        ("ix_engagements_workspace_id", ["workspace_id"]),
        ("ix_engagements_approved_by", ["approved_by"]),
    ]:
        if not _has_index(bind, "engagements", idx):
            op.create_index(idx, "engagements", cols, unique=False)
    # Normalize engagement.organization_id FK to canonical SET NULL.
    if _has_fk(bind, "engagements", "fk_engagements_organization_id") and not _has_fk(
        bind, "engagements", "fk_engagements_organization_id_organizations"
    ):
        op.drop_constraint("fk_engagements_organization_id", "engagements", type_="foreignkey")
    if not _has_fk(bind, "engagements", "fk_engagements_organization_id_organizations"):
        op.create_foreign_key(
            "fk_engagements_organization_id_organizations",
            "engagements",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_fk(bind, "engagements", "fk_engagements_workspace_id_workspaces"):
        op.create_foreign_key(
            "fk_engagements_workspace_id_workspaces",
            "engagements",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_fk(bind, "engagements", "fk_engagements_approved_by_users"):
        op.create_foreign_key(
            "fk_engagements_approved_by_users",
            "engagements",
            "users",
            ["approved_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # Evidence canonical columns
    for col, coltype in [
        ("organization_id", sa.UUID()),
        ("engagement_id", sa.UUID()),
        ("sha256", sa.String(length=64)),
        ("collector", sa.String(length=255)),
        ("tool", sa.String(length=255)),
        ("tool_version", sa.String(length=100)),
    ]:
        if not _has_column(bind, "evidence", col):
            op.add_column("evidence", sa.Column(col, coltype, nullable=True))
    for idx, cols in [
        ("ix_evidence_organization_id", ["organization_id"]),
        ("ix_evidence_engagement_id", ["engagement_id"]),
        ("ix_evidence_sha256", ["sha256"]),
    ]:
        if not _has_index(bind, "evidence", idx):
            op.create_index(idx, "evidence", cols, unique=False)
    if _has_fk(bind, "evidence", "fk_evidence_organization_id") and not _has_fk(
        bind, "evidence", "fk_evidence_organization_id_organizations"
    ):
        op.drop_constraint("fk_evidence_organization_id", "evidence", type_="foreignkey")
    if not _has_fk(bind, "evidence", "fk_evidence_organization_id_organizations"):
        op.create_foreign_key(
            "fk_evidence_organization_id_organizations",
            "evidence",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_fk(bind, "evidence", "fk_evidence_engagement_id_engagements"):
        op.create_foreign_key(
            "fk_evidence_engagement_id_engagements",
            "evidence",
            "engagements",
            ["engagement_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Core entity org ids expected by current models.
    for table, ondelete in [
        ("runs", "CASCADE"),
        ("findings", "CASCADE"),
        ("reports", "CASCADE"),
        ("audit_logs", "SET NULL"),
        ("approvals", "CASCADE"),
    ]:
        if not _has_column(bind, table, "organization_id"):
            op.add_column(table, sa.Column("organization_id", sa.UUID(), nullable=True))
        idx = f"ix_{table}_organization_id"
        if not _has_index(bind, table, idx):
            op.create_index(idx, table, ["organization_id"], unique=False)
        fk = f"fk_{table}_organization_id"
        if not _has_fk(bind, table, fk):
            op.create_foreign_key(
                fk, table, "organizations", ["organization_id"], ["id"], ondelete=ondelete
            )

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
    """Downgrade is intentionally non-destructive for merged tenancy heads."""
    pass
