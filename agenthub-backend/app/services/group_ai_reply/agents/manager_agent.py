from __future__ import annotations

from app.services.group_ai_reply.agents.base import BaseRoleAgent
from app.services.group_ai_reply.context import ReplyContext
from app.services.manager_planning_service import manager_tool_build_plan_with_llm


class ManagerRoleAgent(BaseRoleAgent):
    async def chat(self, ctx: ReplyContext, *, text: str) -> str:
        """
        Manager as a chatty object (no planning/execution).
        """
        memory = self.load_memory(ctx)
        # Use internal LLM with project system prompt so it behaves like manager role.
        from app.agent_runtime.internal_llm import internal_llm_chat
        from app.agent_runtime.memory_builder import build_project_system_prompt

        # Manager is a group capability (not an AgentInstance). Use a neutral system prompt.
        system_prompt = (
            "你是群聊项目的管家（Master），负责答疑与协作推进。\n"
            "你可以聊天解答，但除非用户明确要求“出规划图/DAG/落库/执行”，否则不要主动生成任务图或触发执行。\n"
        )
        return await internal_llm_chat(
            text,
            system_prompt=system_prompt,
            runtime_context={"group_type": "project", "group_id": int(ctx.group.id), "user_id": int(ctx.sender.user_ref) if ctx.sender.user_ref else None},
            short_term_messages=memory.short_term_messages,  # type: ignore[arg-type]
        )

    async def build_plan(self, ctx: ReplyContext, *, goal_text: str, extra_context: dict | None = None) -> dict:
        memory = self.load_memory(ctx)
        context = dict(extra_context or {})
        if memory.long_term_text:
            context["memory_preview"] = memory.long_term_text
        context.setdefault("group_id", int(ctx.group.id))
        # If user already answered clarify questions, include them explicitly for planning.
        if "clarify_answers" in context and context.get("clarify_answers"):
            goal_text = f"{goal_text}\n\n[用户补充约束]\n{str(context.get('clarify_answers') or '')}"
        return await manager_tool_build_plan_with_llm(db=ctx.db, goal_text=goal_text, context=context)
