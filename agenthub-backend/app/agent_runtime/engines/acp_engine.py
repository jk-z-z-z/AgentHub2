from __future__ import annotations

from app.agent_runtime.engine import AgentEngine, EngineContext
from app.agent_runtime.acp.external_runner import ACPRunnerConfig, run_acp_tool_loop
from app.agent_runtime.acp.provider_commands import command_for_provider


class ACPToolLoopEngine(AgentEngine):
    async def run(self, *, ctx: EngineContext, req, tool_executor=None) -> tuple[str, dict]:
        if tool_executor is None:
            raise ValueError("ACP engine requires tool_executor")
        provider_type = str(ctx.engine_type).split(":", 1)[1].strip()
        cfg = ACPRunnerConfig(
            provider_type=provider_type,
            command=command_for_provider(provider_type),
            cwd=str(req.runtime_context.get("project_code_cwd") if isinstance(req.runtime_context, dict) else "") or ".",
        )
        final_text, updates = await run_acp_tool_loop(
            cfg=cfg,
            system_prompt=req.system_prompt or "",
            user_prompt=req.input_text,
            tool_executor=tool_executor,
            max_rounds=12,
        )
        return final_text, {"engine": "acp", "provider_type": provider_type, "updates": updates[:20]}
