from __future__ import annotations

from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import build_short_term_history_msgs
from app.services.group_ai_reply.memory.base import MemoryBundle, MemoryStrategy
from app.services.storage_paths import project_dir


class ProjectMemoryStrategy(MemoryStrategy):
    def load(self, ctx: ReplyContext) -> MemoryBundle:
        short_term = build_short_term_history_msgs(
            ctx.db,
            group_id=int(ctx.group.id),
            exclude_message_id=int(ctx.user_message.id),
        )
        long_term_text = ""
        try:
            memory_file = project_dir(int(ctx.group.id)) / "MEMORY.md"
            if memory_file.exists():
                long_term_text = memory_file.read_text(encoding="utf-8")[:6000]
        except Exception:
            long_term_text = ""
        return MemoryBundle(short_term_messages=short_term, long_term_text=long_term_text)
