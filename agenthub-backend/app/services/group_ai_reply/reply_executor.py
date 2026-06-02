from __future__ import annotations

import json

from fastapi.encoders import jsonable_encoder

from app.common.event_types import WsEventType
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.services.group_ai_reply.strategies.bootstrap_auto import BootstrapAutoReplyStrategy
from app.services.group_ai_reply.strategies.noop import NoopStrategy
from app.services.group_ai_reply.strategies.personal_auto import PersonalAutoReplyStrategy
from app.services.group_ai_reply.strategies.project_manager import ProjectManagerMentionStrategy
from app.services.group_ai_reply.strategies.project_mentions import ProjectMentionedAgentsStrategy
from app.services.message_event_service import create_message_event
from app.agent_runtime.message_store import update_message
from app.ws.manager import ws_manager


class ReplyExecutor:
    def __init__(self) -> None:
        self._strategies: list[ReplyStrategy] = [
            BootstrapAutoReplyStrategy(),
            PersonalAutoReplyStrategy(),
            ProjectManagerMentionStrategy(),
            ProjectMentionedAgentsStrategy(),
            NoopStrategy(),
        ]

    async def execute(self, ctx: ReplyContext) -> None:
        try:
            for strategy in self._strategies:
                if strategy.matches(ctx):
                    await strategy.reply(ctx)
                    break
            if ctx.ai_message is not None:
                create_message_event(
                    ctx.db,
                    message_id=int(ctx.ai_message.id),
                    event_type="reply.executor.finish",
                    payload={"group_id": int(ctx.group.id), "sender_member_id": int(ctx.sender.id)},
                )
        except Exception as e:
            if ctx.ai_message is not None:
                create_message_event(
                    ctx.db,
                    message_id=int(ctx.ai_message.id),
                    event_type="reply.executor.error",
                    payload={"group_id": int(ctx.group.id), "sender_member_id": int(ctx.sender.id), "error": str(e)},
                )
                meta = {}
                try:
                    meta = json.loads(str(ctx.ai_message.metadata_json or "{}"))
                except Exception:
                    meta = {}
                meta["status"] = "failed"
                await update_message(
                    ctx.db,
                    message_id=int(ctx.ai_message.id),
                    content="AI 回复失败，请稍后重试。",
                    meta_json=json.dumps(meta, ensure_ascii=False),
                )
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
