from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from anomaly_core.models import Engagement, Run
from anomaly_core.rbac import engagement_accessible
from anomaly_api.deps import CurrentUser, DbSession, require_engagement_access
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

router = APIRouter(tags=["websocket"])


class ConnectionManager:
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


manager = ConnectionManager()


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
