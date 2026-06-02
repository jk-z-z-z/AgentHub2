from __future__ import annotations

import asyncio

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.common.event_types import WsEventType
from app.db.session import SessionLocal
from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.services.group_ai_reply import ReplyContext, ReplyExecutor
from app.agent_runtime.message_store import create_message
from app.ws.manager import ws_manager


def list_messages(db: Session, group_id: int, cursor: int | None = None, limit: int = 50) -> list[type[Message]]:
    query = db.query(Message).filter(Message.group_id == group_id)
    if cursor is not None:
        query = query.filter(Message.id < cursor)
    rows = query.order_by(Message.id.desc()).limit(min(limit, 100)).all()
    rows.reverse()
    return rows


async def create_message_and_trigger_ai(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> Message:
    user_message = await create_message(db, group_id=group_id, sender_member_id=sender_member_id, message_type=message_type, content=content, meta_json=meta_json)

    # UX: acknowledge immediately so the frontend can show "sent" even if AI reply is slow.
    try:
        await ws_manager.broadcast(
            int(group_id),
            jsonable_encoder(
                {
                    "event": WsEventType.MESSAGE_ACCEPTED,
                    "data": {
                        "group_id": int(group_id),
                        "message_id": int(user_message.id),
                    },
                }
            ),
        )
    except Exception:
        pass

    sender = db.query(Member).filter(Member.id == sender_member_id).first()
    if not sender or sender.kind != "user":
        return user_message
    if message_type != "text":
        return user_message

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return user_message
    executor = ReplyExecutor()
    # Fire-and-forget: avoid blocking HTTP response on slow LLM/tooling.
    async def _run_reply():
        local_db = SessionLocal()
        try:
            local_sender = local_db.query(Member).filter(Member.id == int(sender_member_id)).first()
            local_group = local_db.query(Group).filter(Group.id == int(group_id)).first()
            local_user_message = local_db.query(Message).filter(Message.id == int(user_message.id)).first()
            if not local_sender or not local_group or not local_user_message:
                return
            await executor.execute(
                ReplyContext(
                    db=local_db,
                    group=local_group,
                    sender=local_sender,
                    user_message=local_user_message,
                    content=content,
                    meta_json=meta_json,
                    emit_message=create_message,
                )
            )
        except Exception:
            # errors are already broadcast as reply.failed by executor
            return
        finally:
            local_db.close()

    try:
        asyncio.create_task(_run_reply())
    except RuntimeError:
        # If no running loop (shouldn't happen in FastAPI async endpoint), fall back to await.
        await _run_reply()
    return user_message
