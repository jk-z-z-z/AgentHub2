from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
) -> MessageEvent:
    message = db.query(Message).filter(Message.id == int(message_id)).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    event = MessageEvent(
        message_id=int(message_id),
        seq=_next_seq(db, message_id=int(message_id)),
        event_type=str(event_type),
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
