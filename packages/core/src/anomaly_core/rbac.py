from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from anomaly_core.models import (
    Engagement,
    EngagementMember,
    Permission,
    Role,
    RoleName,
    User,
)

ROLE_RANK: dict[RoleName, int] = {
    RoleName.client_viewer: 1,
    RoleName.pentester: 2,
    RoleName.admin: 3,
}

DEFAULT_PERMISSIONS: dict[RoleName, set[str]] = {
    RoleName.admin: {"*"},
    RoleName.pentester: {
        "engagements.read",
        "engagements.write",
        "findings.read",
        "findings.write",
        "findings.delete",
        "runs.read",
        "runs.write",
        "reports.read",
    },
    RoleName.client_viewer: {
        "engagements.read",
        "findings.read",
        "reports.read",
    },
}

_ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.admin: "Full platform administrator",
    RoleName.pentester: "Runs tools and manages findings",
    RoleName.client_viewer: "Read-only access to an engagement",
}


def _permission_description(name: str) -> str:
    if name == "*":
        return "All permissions"
    return f"Allows {name}"


async def ensure_default_rbac(db: AsyncSession) -> None:
    """Idempotently seed roles, permissions, and role-permission links."""
    roles = {
        role.name: role
        for role in (await db.scalars(select(Role).options(selectinload(Role.permissions)))).all()
    }
    for name, description in _ROLE_DESCRIPTIONS.items():
        if name not in roles:
            db.add(Role(name=name, description=description))
    await db.flush()

    # Reload so newly created roles carry their (empty) permission collections
    # without triggering an async lazy-load.
    roles = {
        role.name: role
        for role in (await db.scalars(select(Role).options(selectinload(Role.permissions)))).all()
    }

    permission_names = {name for names in DEFAULT_PERMISSIONS.values() for name in names}
    permissions = {
        permission.name: permission
        for permission in (
            await db.scalars(select(Permission).options(selectinload(Permission.roles)))
        ).all()
    }
    for perm_name in sorted(set(permission_names) - set(permissions)):
        db.add(Permission(name=perm_name, description=_permission_description(perm_name)))
    await db.flush()

    # Reload so newly created objects have loaded collections (no async lazy-load).
    roles = {
        role.name: role
        for role in (await db.scalars(select(Role).options(selectinload(Role.permissions)))).all()
    }
    permissions = {
        permission.name: permission
        for permission in (
            await db.scalars(select(Permission).options(selectinload(Permission.roles)))
        ).all()
    }

    for role_name, names in DEFAULT_PERMISSIONS.items():
        role = roles[role_name]
        existing = {permission.name for permission in role.permissions}
        for role_perm_name in sorted(names):
            if role_perm_name not in existing:
                role.permissions.append(permissions[role_perm_name])
    await db.flush()
    await db.commit()


def has_role(user: User, role: RoleName) -> bool:
    return any(user_role.name == role for user_role in user.roles)


def has_permission(user: User, permission: str) -> bool:
    return any(
        granted.name == "*" or granted.name == permission
        for role in user.roles
        for granted in role.permissions
    )


async def get_membership(
    db: AsyncSession, user: User, engagement: Engagement
) -> EngagementMember | None:
    result = await db.scalar(
        select(EngagementMember).where(
            EngagementMember.engagement_id == engagement.id,
            EngagementMember.user_id == user.id,
        )
    )
    return result if result is not None else None


async def engagement_accessible(
    db: AsyncSession,
    user: User,
    engagement: Engagement,
    min_role: RoleName = RoleName.client_viewer,
) -> bool:
    if has_role(user, RoleName.admin):
        return True

    org_id = getattr(engagement, "organization_id", None)
    if org_id is not None:
        from anomaly_core.models.tenancy import Membership

        org_member = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org_id,
            )
        )
        if org_member is None:
            return False

    membership = await get_membership(db, user, engagement)
    if membership is None:
        return False
    return ROLE_RANK[membership.role] >= ROLE_RANK[min_role]


async def add_member(
    db: AsyncSession,
    engagement: Engagement,
    user: User,
    role: RoleName = RoleName.pentester,
) -> EngagementMember:
    membership = EngagementMember(
        engagement_id=engagement.id,
        user_id=user.id,
        role=role,
    )
    db.add(membership)
    await db.flush()
    return membership


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)
