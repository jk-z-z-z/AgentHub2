from __future__ import annotations

import asyncio
import json

from sqlalchemy.orm import Session

from app.agent_runtime.message_store import create_message, dispatch_latest_message_event, update_message
from app.event_runtime.facade import create_message_event
from app.event_runtime.types import MessageEventType
from app.models.message import Message


def build_reply_metadata(*, reply_to_message_id: int, trigger: str, status: str | None = None) -> str:
    payload = {
        "reply_to": str(reply_to_message_id),
        "trigger": trigger,
    }
    if status:
        payload["status"] = status
    return json.dumps(payload, ensure_ascii=False)


async def emit_ai_reply(
    db: Session,
    *,
    group_id: int,
    user_message_id: int,
    sender_member_id: int,
    content: str,
    trigger: str,
    ai_message_id: int | None = None,
    status: str = "done",
) -> Message:
    meta_json = build_reply_metadata(reply_to_message_id=int(user_message_id), trigger=trigger, status=status)
    if ai_message_id is not None:
        message = await update_message(
            db,
            message_id=int(ai_message_id),
            content=content,
            meta_json=meta_json,
        )
    else:
        message = await create_message(
            db,
            group_id=int(group_id),
            sender_member_id=int(sender_member_id),
            message_type="ai",
            content=content,
            meta_json=meta_json,
        )
    create_message_event(
        db,
        message_id=int(message.id),
        event_type=(
            MessageEventType.InputOutput.REPLY_FAILED if str(status).lower() == "failed" else MessageEventType.InputOutput.REPLY_FINISHED
        ),
        payload={
            "reply_to_message_id": int(user_message_id),
            "trigger": str(trigger),
            "status": str(status),
            "content": str(content or ""),
        },
    )
    if str(status).lower() == "done":
        try:
            asyncio.create_task(
                dispatch_latest_message_event(
                    group_id=int(group_id),
                    sender_member_id=int(sender_member_id),
                    message_id=int(message.id),
                    message_type=str(message.message_type),
                    content=str(message.content or ""),
                    meta_json=str(message.metadata_json or "{}"),
                )
            )
        except RuntimeError:
            await dispatch_latest_message_event(
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_id=int(message.id),
                message_type=str(message.message_type),
                content=str(message.content or ""),
                meta_json=str(message.metadata_json or "{}"),
            )
    return message
