from __future__ import annotations

from app.agent_runtime.memory_builder import build_personal_system_prompt, build_project_system_prompt
from app.agent_runtime.agent_run_executor import execute_agent_run
from app.services.group_ai_reply.agents.base import BaseRoleAgent
from app.services.group_ai_reply.context import ReplyContext


class AssistantRoleAgent(BaseRoleAgent):
    async def run_personal(self, ctx: ReplyContext, *, agent_id: int, user_id: int) -> str:
        memory = self.load_memory(ctx)
        system_prompt = build_personal_system_prompt(agent_id=agent_id, user_id=user_id)
        exec_res = await execute_agent_run(
            ctx.db,
            group_id=int(ctx.group.id),
            agent_instance_id=int(agent_id),
            input_text=str(ctx.content or ""),
            system_prompt=system_prompt,
            runtime_context={"group_type": "personal", "group_id": int(ctx.group.id), "user_id": int(user_id)},
            short_term_messages=memory.short_term_messages,
            trigger_message_id=int(ctx.user_message.id),
            mode="chat",
        )
        return exec_res.result.text

    async def run_project(self, ctx: ReplyContext, *, agent_id: int) -> str:
        memory = self.load_memory(ctx)
        system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(ctx.group.id))
        exec_res = await execute_agent_run(
            ctx.db,
            group_id=int(ctx.group.id),
            agent_instance_id=int(agent_id),
            input_text=str(ctx.content or ""),
            system_prompt=system_prompt,
            runtime_context={
                "group_type": "project",
                "group_id": int(ctx.group.id),
                "user_id": int(ctx.sender.user_ref) if ctx.sender.user_ref else None,
            },
            short_term_messages=memory.short_term_messages,
            trigger_message_id=int(ctx.user_message.id),
            mode="chat",
        )
        return exec_res.result.text
