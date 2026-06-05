from __future__ import annotations

import asyncio

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.agent_runtime.message_store import create_message, dispatch_message_created_event
from app.event_runtime.context import extract_agent_mentions
from app.ws_runtime import WsEventType, ws_manager


def _extract_agent_mentions(meta_json: str) -> list[int]:
    return extract_agent_mentions(meta_json)


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
    # Fire-and-forget: avoid blocking HTTP response on slow LLM/tooling.
    try:
        asyncio.create_task(
            dispatch_message_created_event(
                group_id=int(group.id),
                sender_member_id=int(sender_member_id),
                message_id=int(user_message.id),
                message_type=str(message_type),
                content=str(content),
                meta_json=str(meta_json),
            )
        )
    except RuntimeError:
        # If no running loop (shouldn't happen in FastAPI async endpoint), fall back to await.
        await dispatch_message_created_event(
            group_id=int(group.id),
            sender_member_id=int(sender_member_id),
            message_id=int(user_message.id),
            message_type=str(message_type),
            content=str(content),
            meta_json=str(meta_json),
        )
    return user_message
