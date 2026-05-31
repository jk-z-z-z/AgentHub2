from __future__ import annotations

import asyncio

from app.models.agent_instance import AgentInstance
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member
from app.services.group_ai_reply.agent_factory import AgentFactory
from app.services.group_ai_reply.agents.assistant_agent import AssistantRoleAgent
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import extract_agent_mentions
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.services.group_task.manager_service import get_or_create_manager_member
from app.services.memory_compressor_service import maybe_compress_project_memory


class ProjectMentionedAgentsStrategy(ReplyStrategy):
    def __init__(self, *, factory: AgentFactory) -> None:
        self._agent: AssistantRoleAgent = factory.build_project_assistant()

    def matches(self, ctx: ReplyContext) -> bool:
        return str(ctx.group.type) == "project" and bool(extract_agent_mentions(ctx.meta_json))

    async def reply(self, ctx: ReplyContext) -> None:
        mentioned_ids = extract_agent_mentions(ctx.meta_json)
        manager_member_id = self._resolve_manager_member_id(ctx)
        await asyncio.gather(*[self._reply_single_agent(ctx, member_id, manager_member_id) for member_id in mentioned_ids])

    def _resolve_manager_member_id(self, ctx: ReplyContext) -> int | None:
        cfg = ctx.db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(ctx.group.id)).first()
        if not cfg or int(cfg.enabled) != 1:
            return None
        return int(get_or_create_manager_member(ctx.db, group_id=int(ctx.group.id)).id)

    async def _reply_single_agent(self, ctx: ReplyContext, agent_member_id: int, manager_member_id: int | None) -> None:
        if manager_member_id is not None and int(agent_member_id) == manager_member_id:
            return
        agent_member = ctx.db.query(Member).filter(Member.id == int(agent_member_id)).first()
        if not agent_member or agent_member.kind != "agent" or int(agent_member.group_id) != int(ctx.group.id):
            return
        if not agent_member.agent_instance_id:
            return
        agent = ctx.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent:
            return
        try:
            await maybe_compress_project_memory(ctx.db, project_id=int(ctx.group.id), agent_id=int(agent.id))
        except Exception:
            pass
        reply_text = await self._agent.run_project(ctx, agent_id=int(agent.id))
        await emit_ai_reply(ctx, sender_member_id=int(agent_member.id), content=reply_text, trigger="mention")
