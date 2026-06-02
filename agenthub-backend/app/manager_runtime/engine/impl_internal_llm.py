from __future__ import annotations

import json
from typing import Any

from app.manager_runtime.engine.base import BaseManagerEngine, ManagerEngineContext
from app.manager_runtime.assistant.planning import manager_tool_build_plan_with_llm
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
        purpose = str(getattr(req, "purpose", "chat") or "chat").strip().lower()
        system_prompt = str(getattr(req, "system_prompt", "") or "")
        runtime_context = dict(getattr(req, "runtime_context", {}) or {})

        if purpose == "plan":
            goal_text = str(getattr(req, "input_text", "") or "").strip()
            plan = await manager_tool_build_plan_with_llm(
                db=getattr(req, "db", None),
                goal_text=goal_text,
                context=runtime_context,
            )
            return json.dumps(plan, ensure_ascii=False), {"engine": "manager_internal_llm", "plan": plan}

        input_text = str(getattr(req, "input_text", "") or "").strip()
        reply = await simple_internal_llm_chat(
            input_text,
            system_prompt=system_prompt,
            short_term_messages=getattr(req, "short_term_memory", None) or [],
        )
        return str(reply), {"engine": "manager_internal_llm"}
