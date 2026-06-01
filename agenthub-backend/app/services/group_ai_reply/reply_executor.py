from __future__ import annotations

from fastapi.encoders import jsonable_encoder

from app.common.event_types import WsEventType
from app.services.group_ai_reply.agent_factory import AgentFactory
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.engine import GroupAiReplyEngine
from app.ws.manager import ws_manager


class ReplyExecutor:
    def __init__(self, *, factory: AgentFactory | None = None) -> None:
        self._factory = factory or AgentFactory()
        self._engine = GroupAiReplyEngine(factory=self._factory)

    async def execute(self, ctx: ReplyContext) -> None:
        try:
            await self._engine.handle(ctx)
        except Exception as e:
            await ws_manager.broadcast(
                int(ctx.group.id),
                jsonable_encoder(
                    {
                        "event": WsEventType.REPLY_FAILED,
                        "data": {
                            "group_id": int(ctx.group.id),
                            "message_id": int(ctx.user_message.id),
                            "sender_member_id": int(ctx.sender.id),
                            "error": str(e),
                        },
                    }
                ),
            )
            raise
