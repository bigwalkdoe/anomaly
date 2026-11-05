from __future__ import annotations

import uuid
from typing import Annotated

from anomaly_core.db import SessionLocal
from anomaly_core.models import Engagement, Run, User
from anomaly_core.rbac import engagement_accessible
from anomaly_core.auth import decode_token
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for run-specific updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        self.active_connections.setdefault(run_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id] = [
                ws for ws in self.active_connections[run_id] if ws != websocket
            ]
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection in list(self.active_connections[run_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(connection, run_id)


class NotificationManager:
    """Manages WebSocket connections for user-specific notifications."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(connection, user_id)

    async def broadcast_to_all(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, message)


manager = ConnectionManager()
notification_manager = NotificationManager()


@router.websocket("/api/ws/runs/{run_id}")
async def run_websocket(
    websocket: WebSocket,
    run_id: str,
):
    await manager.connect(websocket, run_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(run_id, {"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)


@router.get("/api/ws/runs/{run_id}/status")
async def run_ws_status(run_id: str, user: CurrentUser, db: DbSession):
    try:
        rid = UUID(str(run_id))
    except Exception:
        return {"active": False}
    run = await db.get(Run, rid)
    if run is None:
        return {"active": False}
    active = run_id in manager.active_connections and len(manager.active_connections[run_id]) > 0
    return {"active": active, "connection_count": len(manager.active_connections.get(run_id, []))}


@router.websocket("/api/ws/notifications")
async def notification_websocket(
    websocket: WebSocket,
    token: str | None = None,
):
    # Authenticate via token query parameter
    if token is None:
        await websocket.close(code=4001, reason="Missing token")
        return

    from anomaly_core.auth import decode_token
    from anomaly_core.models import User

    try:
        payload = decode_token(token)
        if payload.type != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        user_id = uuid.UUID(payload.sub)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            await websocket.close(code=4001, reason="User not found or inactive")
            return

        user_id_str = str(user.id)
        await notification_manager.connect(websocket, user_id_str)
        try:
            while True:
                data = await websocket.receive_text()
                await notification_manager.broadcast_to_user(user_id_str, {"type": "ack", "data": data})
        except WebSocketDisconnect:
            notification_manager.disconnect(websocket, user_id_str)
