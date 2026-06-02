from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ManagerEngineContext:
    group_id: int
    engine_type: str
    engine_config_json: str


class BaseManagerEngine:
    async def run(
        self,
        *,
        ctx: ManagerEngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError
