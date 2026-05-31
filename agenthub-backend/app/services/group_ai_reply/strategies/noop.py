from __future__ import annotations

from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.strategies.base import ReplyStrategy


class NoopStrategy(ReplyStrategy):
    def matches(self, ctx: ReplyContext) -> bool:
        return True

    async def reply(self, ctx: ReplyContext) -> None:
        return
