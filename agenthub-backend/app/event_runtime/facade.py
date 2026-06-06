from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.event_runtime.types import (
    MessageEventCategory,
    MessageEventStatus,
    describe_message_event_operation as _describe_message_event_operation,
)
from app.models.message import Message
from app.models.message_event import MessageEvent


def _next_seq(db: Session, *, message_id: int) -> int:
    latest = (
        db.query(MessageEvent)
        .filter(MessageEvent.message_id == int(message_id))
        .order_by(MessageEvent.seq.desc())
        .first()
    )
    return int(latest.seq) + 1 if latest else 1


def _infer_event_category(event_type: str) -> str:
    event_type = str(event_type or "")
    if event_type.startswith(("message.", "reply.")):
        return MessageEventCategory.INPUT_OUTPUT
    if event_type.startswith(("bootstrap.", "memory.compression.")):
        return MessageEventCategory.SYSTEM
    if event_type.startswith(("node.exec.", "tool.", "run.", "llm.", "thinking", "stream.", "retry", "error")):
        return MessageEventCategory.EXECUTION
    if event_type.startswith(("dag.", "node.", "branch.")):
        return MessageEventCategory.DAG
    if event_type.startswith(("task.", "assign.", "claim.", "review.")):
        return MessageEventCategory.TASK
    return MessageEventCategory.SYSTEM


def list_message_events(db: Session, *, message_id: int) -> list[MessageEvent]:
    return (
        db.query(MessageEvent)
        .filter(MessageEvent.message_id == int(message_id))
        .order_by(MessageEvent.seq.asc())
        .all()
    )


def create_message_event(
    db: Session,
    *,
    message_id: int,
    event_type: str,
    payload: dict | None = None,
    category: str | None = None,
    status: str = MessageEventStatus.PENDING,
    run_id: int | None = None,
) -> MessageEvent:
    message = db.query(Message).filter(Message.id == int(message_id)).first()
    if not message:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Message not found")
    event_payload = payload or {}
    if run_id is None and isinstance(event_payload, dict):
        maybe_run_id = event_payload.get("run_id")
        try:
            run_id = int(maybe_run_id) if maybe_run_id not in (None, "") else None
        except (TypeError, ValueError):
            run_id = None
    event = MessageEvent(
        message_id=int(message_id),
        run_id=int(run_id) if run_id is not None else None,
        seq=_next_seq(db, message_id=int(message_id)),
        event_type=str(event_type),
        category=str(category or _infer_event_category(event_type)),
        status=str(status or MessageEventStatus.PENDING),
        payload_json=json.dumps(event_payload, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_message_event_status(
    db: Session,
    *,
    event_id: int,
    status: str,
    payload: dict | None = None,
) -> MessageEvent:
    event = db.query(MessageEvent).filter(MessageEvent.id == int(event_id)).first()
    if not event:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Message event not found")
    event.status = str(status)
    if payload is not None:
        event.payload_json = json.dumps(payload, ensure_ascii=False)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def describe_message_event_operation(event_type: str) -> str:
    return _describe_message_event_operation(event_type)


def _event_payload(event: MessageEvent) -> dict[str, Any]:
    try:
        payload = json.loads(event.payload_json or "{}")
        return payload if isinstance(payload, dict) else {"value": payload}
    except Exception:
        return {"raw": str(event.payload_json or "")}


def _event_text(event: MessageEvent) -> str:
    payload = _event_payload(event)
    for key in ("content", "text", "reply_text", "summary", "message", "value"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def list_group_message_event_feed(
    db: Session,
    *,
    group_id: int,
    exclude_message_id: int | None = None,
    after_message_id: int | None = None,
    limit_messages: int = 80,
) -> list[dict[str, Any]]:
    query = db.query(Message).filter(Message.group_id == int(group_id))
    if exclude_message_id is not None:
        query = query.filter(Message.id != int(exclude_message_id))
    if after_message_id is not None:
        query = query.filter(Message.id > int(after_message_id))
    messages = query.order_by(Message.id.desc()).limit(max(1, int(limit_messages))).all()
    messages.reverse()

    feed: list[dict[str, Any]] = []
    for message in messages:
        events = list_message_events(db, message_id=int(message.id))
        latest_text = ""
        for event in reversed(events):
            latest_text = _event_text(event)
            if latest_text:
                break
        if not latest_text:
            latest_text = str(message.content or "")
        feed.append(
            {
                "message_id": int(message.id),
                "group_id": int(message.group_id),
                "sender_member_id": int(message.sender_member_id),
                "message_type": str(message.message_type),
                "role": "assistant" if str(message.message_type) == "ai" else "user",
                "content": latest_text,
                "events": [
                    {
                        "seq": int(event.seq),
                        "event_type": str(event.event_type),
                        "category": str(event.category),
                        "status": str(event.status),
                        "payload": _event_payload(event),
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    }
                    for event in events
                ],
            }
        )
    return feed


def build_group_short_term_memory_from_events(
    db: Session,
    *,
    group_id: int,
    exclude_message_id: int | None = None,
    limit_messages: int = 80,
) -> list[dict[str, Any]]:
    feed = list_group_message_event_feed(
        db,
        group_id=int(group_id),
        exclude_message_id=exclude_message_id,
        limit_messages=limit_messages,
    )
    return [
        {
            "role": str(item["role"]),
            "content": str(item["content"] or ""),
            "name": str(item["sender_member_id"]),
            "message_id": int(item["message_id"]),
        }
        for item in feed
    ]


def build_group_event_compression_input(
    db: Session,
    *,
    group_id: int,
    exclude_message_id: int | None = None,
    limit_messages: int = 120,
) -> str:
    feed = list_group_message_event_feed(
        db,
        group_id=int(group_id),
        exclude_message_id=exclude_message_id,
        limit_messages=limit_messages,
    )
    lines: list[str] = []
    for item in feed:
        lines.append(
            f"[message {item['message_id']}] role={item['role']} sender={item['sender_member_id']} type={item['message_type']}"
        )
        for event in item["events"]:
            payload = event["payload"]
            payload_text = ""
            if isinstance(payload, dict):
                for key in ("content", "text", "reply_text", "summary"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        payload_text = value.strip()
                        break
                if not payload_text:
                    payload_text = json.dumps(payload, ensure_ascii=False, default=str)
            else:
                payload_text = str(payload)
            lines.append(f"  - {event['event_type']}: {payload_text}")
    return "\n".join(lines)
