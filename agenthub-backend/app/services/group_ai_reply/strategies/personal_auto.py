from __future__ import annotations

from fastapi import HTTPException, status

from app.models.agent_instance import AgentInstance
from app.models.member import Member
from app.agent_runtime import invoke_agent
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import extract_agent_mentions
from app.services.group_ai_reply.memory.personal import PersonalMemoryStrategy
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.agent_runtime.message_store import create_pending_ai_message


class PersonalAutoReplyStrategy(ReplyStrategy):
    def __init__(self) -> None:
        pass

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
        ctx.ai_message = await create_pending_ai_message(
            ctx.db,
            group_id=int(ctx.group.id),
            sender_member_id=int(agent_member.id),
            reply_to_message_id=int(ctx.user_message.id),
            trigger="personal_auto",
        )
        memory = PersonalMemoryStrategy().load(ctx)
        exec_res = await invoke_agent(
            ctx.db,
            agent_id=int(agent.id),
            short_term_messages=memory.short_term_messages,
            extra_context={
                "group_type": "personal",
                "group_id": int(ctx.group.id),
                "user_id": int(user_id),
                "input_text": str(ctx.content or ""),
            },
            trace_message_id=int(ctx.ai_message.id) if ctx.ai_message else None,
        )
        reply_text = exec_res.text
        await emit_ai_reply(ctx, sender_member_id=int(agent_member.id), content=reply_text, trigger="personal_auto")
