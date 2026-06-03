from __future__ import annotations

import json

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.event_runtime.facade import create_message_event
from app.event_runtime.types import MessageEventType
from app.ws_runtime import WsEventType, ws_manager


def _assert_group_and_member(db: Session, *, group_id: int, sender_member_id: int) -> Member:
    if not db.query(Group).filter(Group.id == int(group_id)).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    member = db.query(Member).filter(Member.id == int(sender_member_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender member not found")
    if member.group_id != int(group_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender member does not belong to the group",
        )
    return member


async def broadcast_message_created(message: Message) -> None:
    await ws_manager.broadcast(
        int(message.group_id),
        jsonable_encoder(
            {
                "event": WsEventType.MESSAGE_CREATED,
                "data": {
                    "id": message.id,
                    "group_id": message.group_id,
                    "sender_member_id": message.sender_member_id,
                    "message_type": message.message_type,
                    "content": message.content,
                    "metadata_json": message.metadata_json,
                    "reply_to_message_id": message.reply_to_message_id,
                    "created_at": message.created_at,
                    "updated_at": message.updated_at,
                },
            }
        ),
    )


async def broadcast_message_updated(message: Message) -> None:
    await ws_manager.broadcast(
        int(message.group_id),
        jsonable_encoder(
            {
                "event": WsEventType.MESSAGE_UPDATED,
                "data": {
                    "id": message.id,
                    "group_id": message.group_id,
                    "sender_member_id": message.sender_member_id,
                    "message_type": message.message_type,
                    "content": message.content,
                    "metadata_json": message.metadata_json,
                    "reply_to_message_id": message.reply_to_message_id,
                    "created_at": message.created_at,
                    "updated_at": message.updated_at,
                },
            }
        ),
    )


async def create_message(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> Message:
    _assert_group_and_member(db, group_id=int(group_id), sender_member_id=int(sender_member_id))
    item = Message(
        group_id=int(group_id),
        sender_member_id=int(sender_member_id),
        message_type=str(message_type),
        content=str(content),
        metadata_json=str(meta_json),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    await broadcast_message_created(item)
    create_message_event(
        db,
        message_id=int(item.id),
        event_type=MessageEventType.InputOutput.MESSAGE_CREATED,
        payload={
            "content": str(item.content or ""),
            "message_type": str(item.message_type),
            "sender_member_id": int(item.sender_member_id),
            "reply_to_message_id": int(item.reply_to_message_id) if item.reply_to_message_id else None,
            "metadata_json": str(item.metadata_json or "{}"),
        },
    )
    return item


async def create_pending_ai_message(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    reply_to_message_id: int,
    trigger: str,
) -> Message:
    item = Message(
        group_id=int(group_id),
        sender_member_id=int(sender_member_id),
        message_type="ai",
        content="",
        reply_to_message_id=int(reply_to_message_id),
        metadata_json=json.dumps(
            {"status": "pending", "trigger": trigger, "reply_to": str(int(reply_to_message_id))},
            ensure_ascii=False,
        ),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    await broadcast_message_created(item)
    create_message_event(
        db,
        message_id=int(item.id),
        event_type=MessageEventType.InputOutput.MESSAGE_CREATED,
        payload={
            "content": "",
            "message_type": "ai",
            "sender_member_id": int(sender_member_id),
            "reply_to_message_id": int(reply_to_message_id),
            "metadata_json": str(item.metadata_json or "{}"),
            "status": "pending",
        },
    )
    create_message_event(
        db,
        message_id=int(item.id),
        event_type=MessageEventType.InputOutput.REPLY_PLACEHOLDER_CREATED,
        payload={"trigger": trigger, "reply_to_message_id": int(reply_to_message_id)},
    )
    create_message_event(
        db,
        message_id=int(item.id),
        event_type=MessageEventType.InputOutput.REPLY_STARTED,
        payload={"trigger": trigger, "reply_to_message_id": int(reply_to_message_id)},
    )
    return item


async def update_message(
    db: Session,
    *,
    message_id: int,
    content: str | None = None,
    meta_json: str | None = None,
) -> Message:
    item = db.query(Message).filter(Message.id == int(message_id)).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if content is not None:
        item.content = str(content)
    if meta_json is not None:
        item.metadata_json = str(meta_json)
    db.add(item)
    db.commit()
    db.refresh(item)
    await broadcast_message_updated(item)
    create_message_event(
        db,
        message_id=int(item.id),
        event_type=MessageEventType.InputOutput.MESSAGE_UPDATED,
        payload={
            "content": str(item.content or ""),
            "message_type": str(item.message_type),
            "sender_member_id": int(item.sender_member_id),
            "reply_to_message_id": int(item.reply_to_message_id) if item.reply_to_message_id else None,
            "metadata_json": str(item.metadata_json or "{}"),
        },
    )
    return item
