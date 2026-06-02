from __future__ import annotations

import asyncio

from app.models.agent_instance import AgentInstance
from app.models.member import Member
from app.agent_runtime import invoke_agent
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.helpers import extract_agent_mentions
from app.services.group_ai_reply.memory.project import ProjectMemoryStrategy
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.agent_runtime.message_store import create_pending_ai_message
from app.services.memory_compressor_service import maybe_compress_project_memory


class ProjectMentionedAgentsStrategy(ReplyStrategy):
    def __init__(self) -> None:
        pass

    def matches(self, ctx: ReplyContext) -> bool:
        return str(ctx.group.type) == "project" and bool(extract_agent_mentions(ctx.meta_json))

    async def reply(self, ctx: ReplyContext) -> None:
        mentioned_ids = extract_agent_mentions(ctx.meta_json)
        await asyncio.gather(*[self._reply_single_agent(ctx, member_id) for member_id in mentioned_ids])

    async def _reply_single_agent(self, ctx: ReplyContext, agent_member_id: int) -> None:
        agent_member = ctx.db.query(Member).filter(Member.id == int(agent_member_id)).first()
        if not agent_member or agent_member.kind != "agent" or int(agent_member.group_id) != int(ctx.group.id):
            return
        if not agent_member.agent_instance_id:
            return
        agent = ctx.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent:
            return
        agent_ctx = ReplyContext(
            db=ctx.db,
            group=ctx.group,
            sender=ctx.sender,
            user_message=ctx.user_message,
            content=ctx.content,
            meta_json=ctx.meta_json,
            emit_message=ctx.emit_message,
        )
        try:
            await maybe_compress_project_memory(ctx.db, project_id=int(ctx.group.id), agent_id=int(agent.id))
        except Exception:
            pass
        try:
            agent_ctx.ai_message = await create_pending_ai_message(
                ctx.db,
                group_id=int(ctx.group.id),
                sender_member_id=int(agent_member.id),
                reply_to_message_id=int(ctx.user_message.id),
                trigger="mention",
            )
            memory = ProjectMemoryStrategy().load(agent_ctx)
            exec_res = await invoke_agent(
                ctx.db,
                agent_id=int(agent.id),
                short_term_messages=memory.short_term_messages,
                extra_context={
                    "group_type": "project",
                    "group_id": int(ctx.group.id),
                    "project_id": int(ctx.group.id),
                    "user_id": int(ctx.sender.user_ref) if ctx.sender.user_ref else None,
                    "input_text": str(ctx.content or ""),
                },
                trace_message_id=int(agent_ctx.ai_message.id) if agent_ctx.ai_message else None,
            )
            reply_text = exec_res.text
            await emit_ai_reply(agent_ctx, sender_member_id=int(agent_member.id), content=reply_text, trigger="mention")
        except Exception as e:
            fallback_text = (
                f"@{agent_member.id} 执行失败：{str(e)}\n"
                "我已经记录了这次错误，会继续尝试其他被 @ 的 agent。"
            )
            await emit_ai_reply(agent_ctx, sender_member_id=int(agent_member.id), content=fallback_text, trigger="mention", status="failed")
