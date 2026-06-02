from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agent_runtime.message_store import create_message, update_message
from app.models.message import Message


def build_reply_metadata(*, reply_to_message_id: int, trigger: str, status: str | None = None) -> str:
    payload = {
        "reply_to": str(reply_to_message_id),
        "trigger": trigger,
    }
    if status:
        payload["status"] = status
    return json.dumps(
        payload,
        ensure_ascii=False,
    )


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
        return await update_message(
            db,
            message_id=int(ai_message_id),
            content=content,
            meta_json=meta_json,
        )
    return await create_message(
        db,
        group_id=int(group_id),
        sender_member_id=int(sender_member_id),
        message_type="ai",
        content=content,
        meta_json=meta_json,
    )
