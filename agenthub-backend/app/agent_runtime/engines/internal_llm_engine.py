from __future__ import annotations

from app.agent_runtime.engine import AgentEngine, EngineContext
from app.agent_runtime.internal_llm import internal_llm_chat


class InternalLLMEngine(AgentEngine):
    async def run(self, *, ctx: EngineContext, req, tool_executor=None) -> tuple[str, dict]:
        _ = tool_executor
        text = await internal_llm_chat(
            req.input_text,
            system_prompt=req.system_prompt,
            agent_instance_id=int(ctx.agent_id),
            runtime_context=req.runtime_context,
            short_term_messages=req.short_term_messages,  # type: ignore[arg-type]
        )
        return text, {"engine": "internal_llm"}
