from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    roles = {role.name: role for role in (await db.scalars(select(Role))).all()}
    for name, description in _ROLE_DESCRIPTIONS.items():
        if name not in roles:
            role = Role(name=name, description=description)
            db.add(role)
            roles[name] = role
    await db.flush()

    permission_names = {name for names in DEFAULT_PERMISSIONS.values() for name in names}
    permissions = {
        permission.name: permission
        for permission in (await db.scalars(select(Permission))).all()
    }
    for name in permission_names:
        if name not in permissions:
            permission = Permission(name=name, description=_permission_description(name))
            db.add(permission)
            permissions[name] = permission
    await db.flush()

    for role_name, names in DEFAULT_PERMISSIONS.items():
        role = roles[role_name]
        existing = {permission.name for permission in role.permissions}
        for name in names:
            if name not in existing:
                role.permissions.append(permissions[name])
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
    return await db.scalar(
        select(EngagementMember).where(
            EngagementMember.engagement_id == engagement.id,
            EngagementMember.user_id == user.id,
        )
    )


async def engagement_accessible(
    db: AsyncSession,
    user: User,
    engagement: Engagement,
    min_role: RoleName = RoleName.client_viewer,
) -> bool:
    if has_role(user, RoleName.admin):
        return True
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


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    async def dependency(user: "User") -> "User":  # type: ignore
        # Will be used as a dependency that receives user
        if has_role(user, RoleName.admin):
            return user
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return user

    return dependency
