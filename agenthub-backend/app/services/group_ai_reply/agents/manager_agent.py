from __future__ import annotations

from app.services.group_ai_reply.agents.base import BaseRoleAgent
from app.services.group_ai_reply.context import ReplyContext
from app.services.manager_planning_service import manager_tool_build_plan_with_llm


class ManagerRoleAgent(BaseRoleAgent):
    async def build_plan(self, ctx: ReplyContext, *, goal_text: str, extra_context: dict | None = None) -> dict:
        memory = self.load_memory(ctx)
        context = dict(extra_context or {})
        if memory.long_term_text:
            context["memory_preview"] = memory.long_term_text
        return await manager_tool_build_plan_with_llm(goal_text=goal_text, context=context)
