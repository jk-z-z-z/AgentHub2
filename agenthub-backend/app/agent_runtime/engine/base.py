from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EngineContext:
    agent_id: int
    engine_type: str
    engine_config_json: str


class BaseAgentEngine:
    async def run(
        self,
        *,
        ctx: EngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError
