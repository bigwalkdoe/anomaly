from __future__ import annotations

import asyncio
import uuid

import pytest
from anomaly_api.routers.ws import manager, notification_websocket
from anomaly_core.auth import create_access_token, create_refresh_token, hash_password
from anomaly_core.models import Engagement, Role, RoleName, Run, User
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect


class FakeWebSocket:
    """Minimal stand-in for starlette's WebSocket used to drive the route directly."""

    def __init__(self) -> None:
        self.accepted = False
        self.close_event: tuple[int, str | None] | None = None
        self.sent: list[dict] = []
        self.stop = asyncio.Event()

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.close_event = (code, reason)

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)

    async def receive_text(self) -> str:
        await self.stop.wait()
        raise WebSocketDisconnect(code=1000)


async def _make_user(db_session, email: str) -> User:
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is None:
        role = Role(name=RoleName.admin, description="admin")
        db_session.add(role)
        await db_session.flush()
    user = User(email=email, name=email, password_hash=hash_password("pass"), roles=[role])
    db_session.add(user)
    await db_session.commit()
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, ['admin'])}"}


@pytest.mark.asyncio
async def test_notification_ws_requires_token():
    ws = FakeWebSocket()

    await notification_websocket(ws, token=None)

    assert ws.accepted is False
    assert ws.close_event is not None
    assert ws.close_event[0] == 4001


@pytest.mark.asyncio
async def test_notification_ws_rejects_invalid_token():
    ws = FakeWebSocket()

    await notification_websocket(ws, token="not-a-jwt")

    assert ws.accepted is False
    assert ws.close_event is not None
    assert ws.close_event[0] == 4001


@pytest.mark.asyncio
async def test_notification_ws_rejects_refresh_token(client, db_session):
    user = await _make_user(db_session, "ws-refresh@example.com")
    ws = FakeWebSocket()

    await notification_websocket(ws, token=create_refresh_token(user.id))

    assert ws.accepted is False
    assert ws.close_event is not None
    assert ws.close_event[0] == 4001


@pytest.mark.asyncio
async def test_broadcast_reaches_connected_notification_client(client, db_session):
    user = await _make_user(db_session, "ws-broadcast@example.com")
    ws = FakeWebSocket()
    task = asyncio.create_task(
        notification_websocket(ws, token=create_access_token(user.id, ["admin"]))
    )
    try:
        for _ in range(200):
            if ws.accepted:
                break
            await asyncio.sleep(0.01)
        assert ws.accepted, "websocket never accepted the valid access token"

        resp = await client.post(
            "/api/notifications/broadcast",
            headers=_auth_headers(user),
            json={"title": "Maintenance", "message": "Window at 02:00", "severity": "warning"},
        )

        assert resp.status_code == 200
        assert any(
            msg.get("type") == "notification" and msg.get("title") == "Maintenance"
            for msg in ws.sent
        )
    finally:
        ws.stop.set()
        await asyncio.wait_for(task, timeout=5)


@pytest.mark.asyncio
async def test_run_status_requires_auth(client):
    resp = await client.get(f"/api/ws/runs/{uuid.uuid4()}/status")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_run_status_reports_active_connection(client, db_session):
    user = await _make_user(db_session, "ws-run@example.com")
    engagement = Engagement(name="WS Engagement", owner_id=user.id)
    db_session.add(engagement)
    await db_session.flush()
    run = Run(engagement_id=engagement.id, user_id=user.id, tool="stub")
    db_session.add(run)
    await db_session.commit()

    ws = FakeWebSocket()
    await manager.connect(ws, str(run.id))
    try:
        resp = await client.get(
            f"/api/ws/runs/{run.id}/status",
            headers=_auth_headers(user),
        )

        assert resp.status_code == 200
        assert resp.json() == {"active": True, "connection_count": 1}
    finally:
        manager.disconnect(ws, str(run.id))


@pytest.mark.asyncio
async def test_run_status_unknown_run_is_inactive(client, db_session):
    user = await _make_user(db_session, "ws-run-missing@example.com")

    resp = await client.get(
        f"/api/ws/runs/{uuid.uuid4()}/status",
        headers=_auth_headers(user),
    )

    assert resp.status_code == 200
    assert resp.json() == {"active": False, "connection_count": 0}


@pytest.mark.asyncio
async def test_broadcast_does_not_cross_tenant_boundaries(client, db_session):
    from anomaly_core.models import Membership, Organization

    admin_a = await _make_user(db_session, "ws-broadcast-a@example.com")
    user_b = await _make_user(db_session, "ws-broadcast-b@example.com")

    org_a = Organization(name="WS Org A", slug="ws-org-a")
    org_b = Organization(name="WS Org B", slug="ws-org-b")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    db_session.add(Membership(user_id=admin_a.id, organization_id=org_a.id, role="owner"))
    db_session.add(Membership(user_id=user_b.id, organization_id=org_b.id, role="member"))
    await db_session.commit()

    ws_b = FakeWebSocket()
    task = asyncio.create_task(
        notification_websocket(ws_b, token=create_access_token(user_b.id, ["admin"]))
    )
    try:
        for _ in range(200):
            if ws_b.accepted:
                break
            await asyncio.sleep(0.01)
        assert ws_b.accepted, "websocket never accepted the valid access token"

        resp = await client.post(
            "/api/notifications/broadcast",
            headers=_auth_headers(admin_a),
            json={"title": "Tenant A", "message": "secret", "severity": "info"},
        )
        assert resp.status_code == 200
        await asyncio.sleep(0.05)
        assert not any(
            msg.get("type") == "notification" and msg.get("title") == "Tenant A"
            for msg in ws_b.sent
        )
    finally:
        ws_b.stop.set()
        await asyncio.wait_for(task, timeout=5)
