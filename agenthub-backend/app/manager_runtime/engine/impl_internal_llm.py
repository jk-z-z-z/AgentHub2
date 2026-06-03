from __future__ import annotations

from typing import Any

from app.manager_runtime.engine.base import BaseManagerEngine, ManagerEngineContext
from app.services._zero_deps_ai_helpers import simple_internal_llm_chat


class ManagerInternalLLMEngine(BaseManagerEngine):
    async def run(
        self,
        *,
        ctx: ManagerEngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        _ = tool_executor
        system_prompt = str(getattr(req, "system_prompt", "") or "")

        input_text = str(getattr(req, "input_text", "") or "").strip()
        reply = await simple_internal_llm_chat(
            input_text,
            system_prompt=system_prompt,
            short_term_messages=getattr(req, "short_term_memory", None) or [],
        )
        return str(reply), {"engine": "manager_internal_llm"}
