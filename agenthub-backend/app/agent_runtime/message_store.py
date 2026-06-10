from __future__ import annotations

import json
import threading

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.db.session import SessionLocal
from app.event_runtime.context import extract_reply_to_message_id
from app.event_runtime.types import MessageEventType
from app.ws_runtime import WsEventType, ws_manager


_active_dispatch_message_ids: set[int] = set()
_active_dispatch_guard = threading.Lock()


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


def _try_acquire_message_dispatch(message_id: int) -> bool:
    with _active_dispatch_guard:
        normalized_message_id = int(message_id)
        if normalized_message_id in _active_dispatch_message_ids:
            return False
        _active_dispatch_message_ids.add(normalized_message_id)
        return True


def _release_message_dispatch(message_id: int) -> None:
    with _active_dispatch_guard:
        _active_dispatch_message_ids.discard(int(message_id))


def _find_existing_pending_ai_message(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    reply_to_message_id: int,
    trigger: str,
) -> Message | None:
    rows = (
        db.query(Message)
        .filter(
            Message.group_id == int(group_id),
            Message.sender_member_id == int(sender_member_id),
            Message.message_type == "ai",
            Message.reply_to_message_id == int(reply_to_message_id),
        )
        .order_by(Message.id.desc())
        .limit(8)
        .all()
    )
    for row in rows:
        try:
            payload = json.loads(row.metadata_json or "{}")
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            continue
        if str(payload.get("status") or "").lower() != "pending":
            continue
        if str(payload.get("trigger") or "") != str(trigger):
            continue
        return row
    return None


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
    reply_to_message_id: int | None = None,
) -> Message:
    """
    Create a message row and its initial `message.created` event.

    In this project, `message.created` is the trigger event for the business flow.
    Trace-style events (`llm.*`, `tool.*`, `run.*`, etc.) are still written to
    `message_events`, but they are not dispatched back into the runtime.
    """
    _assert_group_and_member(db, group_id=int(group_id), sender_member_id=int(sender_member_id))
    resolved_reply_to_message_id = reply_to_message_id
    if resolved_reply_to_message_id is None:
        resolved_reply_to_message_id = extract_reply_to_message_id(str(meta_json or "{}"))
    item = Message(
        group_id=int(group_id),
        sender_member_id=int(sender_member_id),
        message_type=str(message_type),
        content=str(content),
        reply_to_message_id=int(resolved_reply_to_message_id) if resolved_reply_to_message_id is not None else None,
        metadata_json=str(meta_json),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    await broadcast_message_created(item)
    from app.event_runtime.facade import create_message_event

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


async def dispatch_message_event_for_message(
    *,
    group_id: int,
    sender_member_id: int,
    message_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> None:
    from app.event_runtime.context import EventDispatchRequest
    from app.event_runtime.dispatcher import dispatch_message_event_chain

    if not _try_acquire_message_dispatch(int(message_id)):
        return
    local_db = SessionLocal()
    try:
        from app.event_runtime.dispatcher import EventDispatchRequest, dispatch_message_event_chain

        await dispatch_message_event_chain(
            EventDispatchRequest(
                db=local_db,
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_id=int(message_id),
                message_type=str(message_type),
                content=str(content),
                meta_json=str(meta_json),
            )
        )
    except Exception:
        # Runtime errors are surfaced by the dispatcher via reply.failed when relevant.
        return
    finally:
        local_db.close()
        _release_message_dispatch(int(message_id))


async def dispatch_specific_message_event_for_message(
    *,
    group_id: int,
    sender_member_id: int,
    message_id: int,
    message_type: str,
    content: str,
    meta_json: str,
    event_id: int,
) -> None:
    from app.event_runtime.dispatcher import EventDispatchRequest, dispatch_message_event

    if not _try_acquire_message_dispatch(int(message_id)):
        return
    local_db = SessionLocal()
    try:
        await dispatch_message_event(
            EventDispatchRequest(
                db=local_db,
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_id=int(message_id),
                message_type=str(message_type),
                content=str(content),
                meta_json=str(meta_json),
                event_id=int(event_id),
            )
        )
    except Exception:
        return
    finally:
        local_db.close()
        _release_message_dispatch(int(message_id))


dispatch_message_created_event = dispatch_message_event_for_message
dispatch_latest_message_event = dispatch_message_event_for_message


async def create_pending_ai_message(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    reply_to_message_id: int,
    trigger: str,
) -> Message:
    existing = _find_existing_pending_ai_message(
        db,
        group_id=int(group_id),
        sender_member_id=int(sender_member_id),
        reply_to_message_id=int(reply_to_message_id),
        trigger=str(trigger),
    )
    if existing is not None:
        return existing
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
    from app.event_runtime.facade import create_message_event

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
    from app.event_runtime.facade import create_message_event

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
