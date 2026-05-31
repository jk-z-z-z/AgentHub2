from __future__ import annotations

from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.memory.base import MemoryBundle, MemoryStrategy


class BaseRoleAgent:
    def __init__(self, memory_strategy: MemoryStrategy) -> None:
        self._memory_strategy = memory_strategy

    def load_memory(self, ctx: ReplyContext) -> MemoryBundle:
        return self._memory_strategy.load(ctx)
