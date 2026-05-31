from __future__ import annotations

import json

from app.models.group_assistant_config import GroupAssistantConfig
from app.services.group_ai_reply.agent_factory import AgentFactory
from app.services.group_ai_reply.agents.manager_agent import ManagerRoleAgent
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import build_short_term_history_msgs, extract_agent_mentions
from app.services.group_ai_reply.reply_utils import build_reply_metadata, emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.services.group_task_service import auto_assign_pending_nodes, get_or_create_manager_member, list_group_task_nodes, run_agent_for_node
from app.services.manager_planning_service import (
    clear_pending_plan,
    load_pending_plan,
    manager_tool_read_group_memory_context,
    manager_tool_upsert_plan,
    save_pending_plan,
)


class ProjectManagerMentionStrategy(ReplyStrategy):
    _confirm_yes = {"确认", "同意", "通过", "approve", "yes", "ok", "可以"}

    def __init__(self, *, factory: AgentFactory) -> None:
        self._agent: ManagerRoleAgent = factory.build_project_manager()

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
            goal_text = str(ctx.content or "").strip()
            pending = load_pending_plan(group_id=int(ctx.group.id))
            if pending and self._is_confirm_text(goal_text):
                manager_reply = await self._handle_confirm(ctx, manager_member_id=int(manager_member.id), pending=pending)
                if manager_reply is None:
                    return
            else:
                manager_reply = await self._handle_draft(ctx, goal_text=goal_text)
        except Exception as e:
            manager_reply = (
                "我已收到任务请求，但本次落库失败。\n"
                f"错误：{str(e)}\n"
                "请检查群管家是否启用、会话是否为项目组，然后重试 @管家。"
            )

        await ctx.emit_message(
            ctx.db,
            int(ctx.group.id),
            int(manager_member.id),
            "ai",
            manager_reply,
            build_reply_metadata(reply_to_message_id=int(ctx.user_message.id), trigger="manager_assistant"),
        )

    def _is_confirm_text(self, goal_text: str) -> bool:
        return str(goal_text or "").strip().lower() in self._confirm_yes

    def _build_short_term_preview(self, ctx: ReplyContext) -> str:
        short_term = build_short_term_history_msgs(
            ctx.db,
            group_id=int(ctx.group.id),
            exclude_message_id=int(ctx.user_message.id),
        )
        short_term_lines: list[str] = []
        for msg_item in short_term[-20:]:
            text = ""
            content_blocks = getattr(msg_item, "content", None)
            if isinstance(content_blocks, list) and content_blocks:
                first = content_blocks[0]
                text = str(first.get("text", "")) if isinstance(first, dict) else str(getattr(first, "text", "") or "")
            short_term_lines.append(f"{getattr(msg_item, 'name', 'user')}: {text}")
        return "\n".join(short_term_lines)

    async def _handle_confirm(self, ctx: ReplyContext, *, manager_member_id: int, pending: dict) -> str | None:
        pending_creator = int(pending.get("creator_member_id") or 0)
        if pending_creator != int(ctx.sender.id):
            manager_reply = "该规划草案仅允许发起人确认。请让发起人回复“确认”。"
            await emit_ai_reply(
                ctx,
                sender_member_id=int(manager_member_id),
                content=manager_reply,
                trigger="manager_assistant",
            )
            return None

        plan = pending.get("plan") or {}
        action, run = manager_tool_upsert_plan(
            ctx.db,
            group_id=int(ctx.group.id),
            creator_member_id=int(pending.get("creator_member_id") or ctx.sender.id),
            trigger_message_id=int(ctx.user_message.id),
            plan=plan,
        )
        clear_pending_plan(group_id=int(ctx.group.id))
        _ = auto_assign_pending_nodes(ctx.db, run_id=int(run.id))
        for node in list_group_task_nodes(ctx.db, run_id=int(run.id)):
            if node.status == "running" and node.assignee_kind == "agent":
                try:
                    await run_agent_for_node(ctx.db, node_id=int(node.id))
                except Exception:
                    pass
        return f"{'已新建' if action == 'created' else '已更新（仅未执行节点）'}并开始分配执行。\nrun_id={run.id}"

    async def _handle_draft(self, ctx: ReplyContext, *, goal_text: str) -> str:
        context = manager_tool_read_group_memory_context(ctx.db, group_id=int(ctx.group.id))
        short_term_text = self._build_short_term_preview(ctx)
        plan = await self._agent.build_plan(
            ctx,
            goal_text=goal_text,
            extra_context={**context, "short_term_preview": short_term_text[:4000]},
        )
        save_pending_plan(group_id=int(ctx.group.id), creator_member_id=int(ctx.sender.id), plan=plan)
        return (
            "我已生成规划草案（已按当前目标校正），请确认是否落库执行（回复：确认 / 同意）。\n\n"
            "```json\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n"
            "```"
        )
