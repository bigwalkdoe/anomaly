"""add tenancy, approval, and evidence integrity fields for vertical slice

Revision ID: bb2c3d4e5f60
Revises: aa1b2c3d4e5f
Create Date: 2026-11-10 14:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bb2c3d4e5f60"
down_revision: str | Sequence[str] | None = "aa1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_enum_values(enum_name: str, values: list[str]) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for value in values:
        op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade() -> None:
    """Upgrade schema."""
    # Tenancy tables
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
    op.create_index(op.f("ix_organizations_created_at"), "organizations", ["created_at"], unique=False)
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

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
    op.create_index(op.f("ix_workspaces_created_at"), "workspaces", ["created_at"], unique=False)
    op.create_index(op.f("ix_workspaces_organization_id"), "workspaces", ["organization_id"], unique=False)
    op.create_index(op.f("ix_workspaces_slug"), "workspaces", ["slug"], unique=False)

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
        sa.UniqueConstraint("user_id", "organization_id", "workspace_id", name="uq_membership_user_org_ws"),
    )
    op.create_index(op.f("ix_memberships_created_at"), "memberships", ["created_at"], unique=False)
    op.create_index(op.f("ix_memberships_organization_id"), "memberships", ["organization_id"], unique=False)
    op.create_index(op.f("ix_memberships_role"), "memberships", ["role"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_memberships_workspace_id"), "memberships", ["workspace_id"], unique=False)

    # Engagement tenancy & approval fields
    op.add_column("engagements", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("engagements", sa.Column("workspace_id", sa.UUID(), nullable=True))
    op.add_column("engagements", sa.Column("approved_by", sa.UUID(), nullable=True))
    op.add_column("engagements", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_engagements_organization_id"), "engagements", ["organization_id"], unique=False)
    op.create_index(op.f("ix_engagements_workspace_id"), "engagements", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_engagements_approved_by"), "engagements", ["approved_by"], unique=False)
    op.create_foreign_key(
        "fk_engagements_organization_id_organizations",
        "engagements",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_engagements_workspace_id_workspaces",
        "engagements",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_engagements_approved_by_users",
        "engagements",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Extend engagement status enum values (Postgres)
    _add_enum_values(
        "engagementstatus",
        ["pending_approval", "approved", "completed", "archived"],
    )

    # Evidence integrity/provenance fields
    op.add_column("evidence", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("evidence", sa.Column("engagement_id", sa.UUID(), nullable=True))
    op.add_column("evidence", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("evidence", sa.Column("collector", sa.String(length=255), nullable=True))
    op.add_column("evidence", sa.Column("tool", sa.String(length=255), nullable=True))
    op.add_column("evidence", sa.Column("tool_version", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_evidence_organization_id"), "evidence", ["organization_id"], unique=False)
    op.create_index(op.f("ix_evidence_engagement_id"), "evidence", ["engagement_id"], unique=False)
    op.create_index(op.f("ix_evidence_sha256"), "evidence", ["sha256"], unique=False)
    op.create_foreign_key(
        "fk_evidence_organization_id_organizations",
        "evidence",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_evidence_engagement_id_engagements",
        "evidence",
        "engagements",
        ["engagement_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_evidence_engagement_id_engagements", "evidence", type_="foreignkey")
    op.drop_constraint("fk_evidence_organization_id_organizations", "evidence", type_="foreignkey")
    op.drop_index(op.f("ix_evidence_sha256"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_engagement_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_organization_id"), table_name="evidence")
    op.drop_column("evidence", "tool_version")
    op.drop_column("evidence", "tool")
    op.drop_column("evidence", "collector")
    op.drop_column("evidence", "sha256")
    op.drop_column("evidence", "engagement_id")
    op.drop_column("evidence", "organization_id")

    op.drop_constraint("fk_engagements_approved_by_users", "engagements", type_="foreignkey")
    op.drop_constraint("fk_engagements_workspace_id_workspaces", "engagements", type_="foreignkey")
    op.drop_constraint("fk_engagements_organization_id_organizations", "engagements", type_="foreignkey")
    op.drop_index(op.f("ix_engagements_approved_by"), table_name="engagements")
    op.drop_index(op.f("ix_engagements_workspace_id"), table_name="engagements")
    op.drop_index(op.f("ix_engagements_organization_id"), table_name="engagements")
    op.drop_column("engagements", "approved_at")
    op.drop_column("engagements", "approved_by")
    op.drop_column("engagements", "workspace_id")
    op.drop_column("engagements", "organization_id")

    op.drop_index(op.f("ix_memberships_workspace_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_user_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_role"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_organization_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_created_at"), table_name="memberships")
    op.drop_table("memberships")

    op.drop_index(op.f("ix_workspaces_slug"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_organization_id"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_created_at"), table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_created_at"), table_name="organizations")
    op.drop_table("organizations")
    # Note: removing enum values from Postgres enums is non-trivial and not performed here.
