from __future__ import annotations

import json

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.services.group_ai_reply import ReplyContext, ReplyExecutor
from app.ws.manager import ws_manager


def list_messages(db: Session, group_id: int, cursor: int | None = None, limit: int = 50) -> list[type[Message]]:
    query = db.query(Message).filter(Message.group_id == group_id)
    if cursor is not None:
        query = query.filter(Message.id < cursor)
    rows = query.order_by(Message.id.desc()).limit(min(limit, 100)).all()
    rows.reverse()
    return rows


async def create_message(db: Session, group_id: int, sender_member_id: int, message_type: str, content: str, meta_json: str) -> Message:
    if not db.query(Group).filter(Group.id == group_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    member = db.query(Member).filter(Member.id == sender_member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender member not found")
    if member.group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender member does not belong to the group",
        )

    item = Message()
    item.group_id = group_id
    item.sender_member_id = sender_member_id
    item.message_type = message_type
    item.content = content
    item.metadata_json = meta_json
    # created_at/updated_at handled by SQLAlchemy defaults/onupdate

    db.add(item)
    db.commit()
    db.refresh(item)
    await ws_manager.broadcast(
        group_id,
        jsonable_encoder(
            {
                "event": "message.created",
                "data": {
                    "id": item.id,
                    "group_id": item.group_id,
                    "sender_member_id": item.sender_member_id,
                    "message_type": item.message_type,
                    "content": item.content,
                    "metadata_json": item.metadata_json,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                },
            }
        ),
    )
    return item


async def create_message_and_trigger_ai(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> Message:
    user_message = await create_message(db, group_id, sender_member_id, message_type, content, meta_json)

    sender = db.query(Member).filter(Member.id == sender_member_id).first()
    if not sender or sender.kind != "user":
        return user_message
    if message_type != "text":
        return user_message

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return user_message
    executor = ReplyExecutor()
    await executor.execute(
        ReplyContext(
            db=db,
            group=group,
            sender=sender,
            user_message=user_message,
            content=content,
            meta_json=meta_json,
            emit_message=create_message,
        )
    )
    return user_message
