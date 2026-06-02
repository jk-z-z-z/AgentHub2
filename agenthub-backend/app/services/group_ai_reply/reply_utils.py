from __future__ import annotations

import json

from app.services.group_ai_reply.context import ReplyContext
from app.agent_runtime.message_store import create_message, update_message


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
    ctx: ReplyContext,
    *,
    sender_member_id: int,
    content: str,
    trigger: str,
    status: str = "done",
) -> None:
    if ctx.ai_message and int(ctx.ai_message.sender_member_id) == int(sender_member_id):
        updated = await update_message(
            ctx.db,
            message_id=int(ctx.ai_message.id),
            content=content,
            meta_json=build_reply_metadata(reply_to_message_id=int(ctx.user_message.id), trigger=trigger, status=status),
        )
        ctx.ai_message = updated
        return
    await create_message(
        ctx.db,
        group_id=int(ctx.group.id),
        sender_member_id=int(sender_member_id),
        message_type="ai",
        content=content,
        meta_json=build_reply_metadata(reply_to_message_id=int(ctx.user_message.id), trigger=trigger, status=status),
    )
