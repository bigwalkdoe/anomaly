from __future__ import annotations

import pytest
from anomaly_core.auth import create_access_token, hash_password
from anomaly_core.models import (
    Engagement,
    EngagementMember,
    EngagementMode,
    Membership,
    Organization,
    Role,
    RoleName,
    User,
)
from sqlalchemy import select


async def _get_role(db_session, role_name: RoleName) -> Role:
    role = await db_session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name, description=role_name.value)
        db_session.add(role)
        await db_session.flush()
    return role


async def _make_user(db_session, role: Role, email: str, name: str) -> User:
    user = User(email=email, name=name, password_hash=hash_password("pass"), roles=[role])
    db_session.add(user)
    await db_session.flush()
    return user


class _FakeMinio:
    def bucket_exists(self, *_args, **_kwargs):
        return True

    def make_bucket(self, *_args, **_kwargs):
        return None

    def put_object(self, *_args, **_kwargs):
        return None


async def _seed_upload_context(db_session, suffix: str):
    owner = await _make_user(
        db_session,
        await _get_role(db_session, RoleName.admin),
        f"upload-owner-{suffix}@example.com",
        "Owner",
    )
    org = Organization(name=f"Upload Org {suffix}", slug=f"upload-org-{suffix}")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=owner.id, organization_id=org.id, role="owner"))
    eng = Engagement(
        name=f"Upload Edge Eng {suffix}",
        mode=EngagementMode.own_infra,
        owner_id=owner.id,
        organization_id=org.id,
    )
    db_session.add(eng)
    await db_session.flush()
    db_session.add(EngagementMember(engagement_id=eng.id, user_id=owner.id, role=RoleName.admin))
    await db_session.commit()
    return owner, eng


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client, db_session, monkeypatch):
    monkeypatch.setattr("anomaly_api.routers.upload.get_minio_client", lambda: _FakeMinio())
    monkeypatch.setattr("anomaly_api.routers.upload.MAX_UPLOAD_SIZE", 10)

    owner, eng = await _seed_upload_context(db_session, "size")
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, [RoleName.admin.value])}"}
    files = {"file": ("big.txt", b"0123456789abcdef", "text/plain")}

    resp = await client.post(f"/api/upload/engagements/{eng.id}", headers=headers, files=files)
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_sanitizes_filename(client, db_session, monkeypatch):
    monkeypatch.setattr("anomaly_api.routers.upload.get_minio_client", lambda: _FakeMinio())

    owner, eng = await _seed_upload_context(db_session, "name")
    headers = {"Authorization": f"Bearer {create_access_token(owner.id, [RoleName.admin.value])}"}
    files = {"file": ("../../evil..name$.txt", b"hello", "text/plain")}

    resp = await client.post(f"/api/upload/engagements/{eng.id}", headers=headers, files=files)
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "evil..name.txt"
    assert ".." not in body["object_name"].split("/", 1)[-1].replace("evil..name.txt", "")
    assert body["size"] == 5
