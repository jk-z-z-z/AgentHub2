from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BootstrapEngineContext:
    agent_id: int
    engine_type: str


class BaseBootstrapEngine:
    async def run(self, *, ctx: BootstrapEngineContext, req: Any) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError
