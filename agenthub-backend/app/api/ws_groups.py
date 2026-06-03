from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import SessionLocal
from app.dependencies.auth import get_active_user_by_token
from app.models.member import Member
from app.ws_runtime import ws_manager


router = APIRouter(tags=["ws"])


@router.websocket("/ws/groups/{group_id}")
async def ws_group(websocket: WebSocket, group_id: int, token: str):
    db = SessionLocal()
    try:
        user = get_active_user_by_token(db, token)
        if not user:
            await websocket.close(code=4401)
            return

        member = (
            db.query(Member)
            .filter(Member.group_id == group_id, Member.kind == "user", Member.user_ref == str(user.id))
            .first()
        )
        if not member:
            await websocket.close(code=4403)
            return

        await ws_manager.connect(group_id, websocket)
        while True:
            # Keep the connection alive and allow client pings; ignore payload.
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(group_id, websocket)
    finally:
        db.close()
