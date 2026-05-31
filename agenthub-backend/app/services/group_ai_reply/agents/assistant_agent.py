from __future__ import annotations

from app.services.ai_service import ai_chat
from app.services.context_builder import build_personal_system_prompt, build_project_system_prompt
from app.services.group_ai_reply.agents.base import BaseRoleAgent
from app.services.group_ai_reply.context import ReplyContext


class AssistantRoleAgent(BaseRoleAgent):
    async def run_personal(self, ctx: ReplyContext, *, agent_id: int, user_id: int) -> str:
        memory = self.load_memory(ctx)
        system_prompt = build_personal_system_prompt(agent_id=agent_id, user_id=user_id)
        return await ai_chat(
            ctx.content,
            system_prompt,
            agent_instance_id=agent_id,
            runtime_context={"group_type": "personal", "group_id": int(ctx.group.id), "user_id": user_id},
            short_term_messages=memory.short_term_messages,
        )

    async def run_project(self, ctx: ReplyContext, *, agent_id: int) -> str:
        memory = self.load_memory(ctx)
        system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(ctx.group.id))
        return await ai_chat(
            ctx.content,
            system_prompt,
            agent_instance_id=agent_id,
            runtime_context={
                "group_type": "project",
                "group_id": int(ctx.group.id),
                "user_id": int(ctx.sender.user_ref) if ctx.sender.user_ref else None,
            },
            short_term_messages=memory.short_term_messages,
        )
