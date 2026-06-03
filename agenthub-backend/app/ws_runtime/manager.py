from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, group_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[group_id].add(websocket)

    def disconnect(self, group_id: int, websocket: WebSocket) -> None:
        if group_id in self.active_connections:
            self.active_connections[group_id].discard(websocket)
            if not self.active_connections[group_id]:
                self.active_connections.pop(group_id, None)

    async def broadcast(self, group_id: int, payload: dict) -> None:
        dead_connections: list[WebSocket] = []
        for websocket in self.active_connections.get(group_id, set()):
            try:
                await websocket.send_json(payload)
            except Exception:
                dead_connections.append(websocket)
        for websocket in dead_connections:
            self.disconnect(group_id, websocket)


ws_manager = ConnectionManager()
