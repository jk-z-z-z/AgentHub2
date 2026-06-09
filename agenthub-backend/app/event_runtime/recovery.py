from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func

from app.agent_runtime.message_store import dispatch_specific_message_event_for_message
from app.core.config import settings
from app.db.session import SessionLocal
from app.event_runtime.types import ACTIVE_DISPATCH_EVENT_TYPES, MessageEventStatus
from app.models.message import Message
from app.models.message_event import MessageEvent


logger = logging.getLogger(__name__)


def _cleanup_non_dispatchable_pending_events(*, limit: int, message_id: int | None = None) -> int:
    db = SessionLocal()
    try:
        query = db.query(MessageEvent).filter(
            MessageEvent.status == MessageEventStatus.PENDING,
            ~MessageEvent.event_type.in_(tuple(ACTIVE_DISPATCH_EVENT_TYPES)),
        )
        if message_id is not None:
            query = query.filter(MessageEvent.message_id == int(message_id))
        rows = query.order_by(MessageEvent.id.asc()).limit(max(1, int(limit))).all()
        if not rows:
            return 0
        for row in rows:
            row.status = MessageEventStatus.DONE
            db.add(row)
        db.commit()
        return len(rows)
    finally:
        db.close()


def _list_pending_message_dispatch_candidates(*, limit: int, message_id: int | None = None) -> list[dict[str, object]]:
    db = SessionLocal()
    try:
        query = (
            db.query(
                MessageEvent.message_id.label("message_id"),
                func.min(MessageEvent.id).label("first_event_id"),
            )
            .filter(
                MessageEvent.status == MessageEventStatus.PENDING,
                MessageEvent.event_type.in_(tuple(ACTIVE_DISPATCH_EVENT_TYPES)),
            )
        )
        if message_id is not None:
            query = query.filter(MessageEvent.message_id == int(message_id))
        rows = query.group_by(MessageEvent.message_id).order_by(func.min(MessageEvent.id).asc()).limit(max(1, int(limit))).all()
        message_ids = [int(row.message_id) for row in rows if getattr(row, "message_id", None) is not None]
        if not message_ids:
            return []
        messages = db.query(Message).filter(Message.id.in_(message_ids)).all()
        messages_by_id = {int(message.id): message for message in messages}
        candidates: list[dict[str, object]] = []
        for row in rows:
            message = messages_by_id.get(int(row.message_id))
            if message is None:
                continue
            candidates.append(
                {
                    "message_id": int(message.id),
                    "group_id": int(message.group_id),
                    "sender_member_id": int(message.sender_member_id),
                    "message_type": str(message.message_type),
                    "content": str(message.content or ""),
                    "meta_json": str(message.metadata_json or "{}"),
                    "event_id": int(row.first_event_id),
                }
            )
        return candidates
    finally:
        db.close()


async def recover_pending_message_event_chains_once(*, limit: int | None = None, message_id: int | None = None) -> int:
    batch_size = int(limit or settings.message_event_recovery_batch_size or 32)
    _cleanup_non_dispatchable_pending_events(
        limit=max(batch_size * 8, 64),
        message_id=message_id,
    )
    candidates = _list_pending_message_dispatch_candidates(limit=batch_size, message_id=message_id)
    recovered = 0
    for candidate in candidates:
        await dispatch_specific_message_event_for_message(
            group_id=int(candidate["group_id"]),
            sender_member_id=int(candidate["sender_member_id"]),
            message_id=int(candidate["message_id"]),
            message_type=str(candidate["message_type"]),
            content=str(candidate["content"]),
            meta_json=str(candidate["meta_json"]),
            event_id=int(candidate["event_id"]),
        )
        recovered += 1
    return recovered


async def run_pending_message_event_recovery_loop() -> None:
    interval_seconds = max(0.2, float(settings.message_event_recovery_interval_seconds or 2.0))
    while True:
        try:
            await recover_pending_message_event_chains_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("pending_message_event_recovery_failed")
        await asyncio.sleep(interval_seconds)
