from __future__ import annotations

from app.models.group_assistant_config import GroupAssistantConfig
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import extract_agent_mentions
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.services.group_task.manager_service import get_or_create_manager_member
from app.agent_runtime.message_store import create_pending_ai_message
from app.manager_runtime import invoke_manager


class ProjectManagerMentionStrategy(ReplyStrategy):
    def __init__(self) -> None:
        pass

    def matches(self, ctx: ReplyContext) -> bool:
        if str(ctx.group.type) != "project":
            return False
        agent_member_ids = extract_agent_mentions(ctx.meta_json)
        if not agent_member_ids:
            return False
        cfg = ctx.db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(ctx.group.id)).first()
        if not cfg or int(cfg.enabled) != 1:
            return False
        manager_member = get_or_create_manager_member(ctx.db, group_id=int(ctx.group.id))
        return int(manager_member.id) in set(agent_member_ids)

    async def reply(self, ctx: ReplyContext) -> None:
        manager_member = get_or_create_manager_member(ctx.db, group_id=int(ctx.group.id))
        try:
            if ctx.ai_message is None:
                ctx.ai_message = await create_pending_ai_message(
                    ctx.db,
                    group_id=int(ctx.group.id),
                    sender_member_id=int(manager_member.id),
                    reply_to_message_id=int(ctx.user_message.id),
                    trigger="manager_runtime",
                )
            memory = self._build_short_term_memory(ctx)
            res = await invoke_manager(
                ctx.db,
                group_id=int(ctx.group.id),
                short_term_memory=memory,
                extra_context={
                    "purpose": "assistant",
                    "input_text": str(ctx.content or ""),
                    "group_type": "project",
                    "group_id": int(ctx.group.id),
                    "user_id": int(ctx.sender.user_ref) if ctx.sender.user_ref else None,
                    "sender_id": int(ctx.sender.id),
                    "user_message_id": int(ctx.user_message.id),
                },
                trace_message_id=int(ctx.ai_message.id) if ctx.ai_message else None,
            )
            manager_reply = res.text
            await emit_ai_reply(
                ctx,
                sender_member_id=int(manager_member.id),
                content=manager_reply,
                trigger="manager_runtime",
            )
        except Exception as e:
            manager_reply = (
                "我已收到任务请求，但本次落库失败。\n"
                f"错误：{str(e)}\n"
                "请检查群管家是否启用、会话是否为项目组，然后重试 @管家。"
            )
            await emit_ai_reply(
                ctx,
                sender_member_id=int(manager_member.id),
                content=manager_reply,
                trigger="manager_runtime",
                status="failed",
            )

    def _build_short_term_memory(self, ctx: ReplyContext) -> list[object]:
        from app.services.group_ai_reply.helpers import build_short_term_history_msgs

        return build_short_term_history_msgs(
            ctx.db,
            group_id=int(ctx.group.id),
            exclude_message_id=int(ctx.user_message.id),
        )
