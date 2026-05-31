from __future__ import annotations

from app.services.group_ai_reply.context import ReplyContext


class ReplyStrategy:
    def matches(self, ctx: ReplyContext) -> bool:
        raise NotImplementedError

    async def reply(self, ctx: ReplyContext) -> None:
        raise NotImplementedError
