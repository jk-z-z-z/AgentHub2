from __future__ import annotations

from dataclasses import dataclass

from app.services.group_ai_reply.context import ReplyContext


@dataclass
class MemoryBundle:
    short_term_messages: list
    long_term_text: str


class MemoryStrategy:
    def load(self, ctx: ReplyContext) -> MemoryBundle:
        raise NotImplementedError
