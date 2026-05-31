from __future__ import annotations

import json

from app.services.group_ai_reply.context import ReplyContext


def build_reply_metadata(*, reply_to_message_id: int, trigger: str) -> str:
    return json.dumps(
        {
            "reply_to": str(reply_to_message_id),
            "trigger": trigger,
        },
        ensure_ascii=False,
    )


async def emit_ai_reply(
    ctx: ReplyContext,
    *,
    sender_member_id: int,
    content: str,
    trigger: str,
) -> None:
    await ctx.emit_message(
        ctx.db,
        int(ctx.group.id),
        int(sender_member_id),
        "ai",
        content,
        build_reply_metadata(reply_to_message_id=int(ctx.user_message.id), trigger=trigger),
    )
