from __future__ import annotations

from app.services.group_ai_reply.agent_factory import AgentFactory
from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.strategies.base import ReplyStrategy
from app.services.group_ai_reply.strategies.noop import NoopStrategy
from app.services.group_ai_reply.strategies.personal_auto import PersonalAutoReplyStrategy
from app.services.group_ai_reply.strategies.project_manager import ProjectManagerMentionStrategy
from app.services.group_ai_reply.strategies.project_mentions import ProjectMentionedAgentsStrategy


class GroupAiReplyEngine:
    def __init__(self, *, factory: AgentFactory | None = None) -> None:
        built_factory = factory or AgentFactory()
        self._strategies: list[ReplyStrategy] = [
            PersonalAutoReplyStrategy(factory=built_factory),
            ProjectManagerMentionStrategy(factory=built_factory),
            ProjectMentionedAgentsStrategy(factory=built_factory),
            NoopStrategy(),
        ]

    async def handle(self, ctx: ReplyContext) -> None:
        for strategy in self._strategies:
            if strategy.matches(ctx):
                await strategy.reply(ctx)
                return
