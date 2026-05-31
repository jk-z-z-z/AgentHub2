from __future__ import annotations

from fastapi import HTTPException, status

from app.models.agent_instance import AgentInstance
from app.models.member import Member
from app.services.group_ai_reply.agent_factory import AgentFactory
from app.services.group_ai_reply.agents.assistant_agent import AssistantRoleAgent
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import extract_agent_mentions
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy


class PersonalAutoReplyStrategy(ReplyStrategy):
    def __init__(self, *, factory: AgentFactory) -> None:
        self._agent: AssistantRoleAgent = factory.build_personal_assistant()

    def matches(self, ctx: ReplyContext) -> bool:
        return str(ctx.group.type) == "personal"

    async def reply(self, ctx: ReplyContext) -> None:
        if extract_agent_mentions(ctx.meta_json):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Personal group does not support mentions")

        agent_member = (
            ctx.db.query(Member).filter(Member.group_id == int(ctx.group.id), Member.kind == "agent").order_by(Member.id.asc()).first()
        )
        if not agent_member or not agent_member.agent_instance_id:
            return
        agent = ctx.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent or not ctx.sender.user_ref:
            return
        try:
            user_id = int(ctx.sender.user_ref)
        except (TypeError, ValueError):
            return

        reply_text = await self._agent.run_personal(ctx, agent_id=int(agent.id), user_id=user_id)
        await emit_ai_reply(ctx, sender_member_id=int(agent_member.id), content=reply_text, trigger="personal_auto")
