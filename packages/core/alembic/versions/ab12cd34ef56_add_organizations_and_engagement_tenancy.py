"""add organizations and engagement tenancy

Revision ID: ab12cd34ef56
Revises: 00ea86254717
Create Date: 2026-11-10 16:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab12cd34ef56"
down_revision: str | Sequence[str] | None = "00ea86254717"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


organization_status = sa.Enum("active", "disabled", name="organizationstatus")
organization_role = sa.Enum("owner", "admin", "member", "viewer", name="organizationrole")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", organization_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organizations_created_at"), "organizations", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
    op.create_index(op.f("ix_organizations_status"), "organizations", ["status"], unique=False)

    op.create_table(
        "organization_members",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "user_id"),
    )
    op.create_index(
        op.f("ix_organization_members_created_at"),
        "organization_members",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_members_role"),
        "organization_members",
        ["role"],
        unique=False,
    )

    op.add_column("engagements", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_engagements_organization_id"),
        "engagements",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_engagements_organization_id",
        "engagements",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_engagements_organization_id", "engagements", type_="foreignkey")
    op.drop_index(op.f("ix_engagements_organization_id"), table_name="engagements")
    op.drop_column("engagements", "organization_id")

    op.drop_index(op.f("ix_organization_members_role"), table_name="organization_members")
    op.drop_index(op.f("ix_organization_members_created_at"), table_name="organization_members")
    op.drop_table("organization_members")

    op.drop_index(op.f("ix_organizations_status"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_created_at"), table_name="organizations")
    op.drop_table("organizations")

    organization_role.drop(op.get_bind(), checkfirst=True)
    organization_status.drop(op.get_bind(), checkfirst=True)
