from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EngineContext:
    agent_id: int
    engine_type: str
    engine_config_json: str


class AgentEngine:
    async def run(self, *, ctx: EngineContext, req, tool_executor=None) -> tuple[str, dict]:
        raise NotImplementedError

