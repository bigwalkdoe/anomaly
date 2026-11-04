from __future__ import annotations

import pytest

from anomaly_core.rbac import ensure_default_rbac
from sqlalchemy import select

from anomaly_core.db import SessionLocal
from anomaly_core.models import Permission, Role, RoleName


@pytest.mark.asyncio
async def test_ensure_default_rbac_is_idempotent(reset_db):
    async with SessionLocal() as first:
        await ensure_default_rbac(first)
    async with SessionLocal() as second:
        await ensure_default_rbac(second)
        roles = (await second.scalars(select(Role))).all()
        permissions = (await second.scalars(select(Permission))).all()
    assert {role.name for role in roles} == set(RoleName)
    assert len(permissions) == 9


@pytest.mark.asyncio
async def test_ensure_default_rbac_links_default_permission_sets(reset_db):
    async with SessionLocal() as session:
        await ensure_default_rbac(session)
        admin = await session.scalar(select(Role).where(Role.name == RoleName.admin))
        pentester = await session.scalar(select(Role).where(Role.name == RoleName.pentester))
        viewer = await session.scalar(select(Role).where(Role.name == RoleName.client_viewer))
    assert admin is not None and pentester is not None and viewer is not None
    assert {p.name for p in admin.permissions} == {"*"}
    assert {p.name for p in pentester.permissions} == {
        "engagements.read",
        "engagements.write",
        "findings.read",
        "findings.write",
        "findings.delete",
        "runs.read",
        "runs.write",
        "reports.read",
    }
    assert {p.name for p in viewer.permissions} == {
        "engagements.read",
        "findings.read",
        "reports.read",
    }
