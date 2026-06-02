from __future__ import annotations

from typing import Any

from app.agent_runtime.engine.base import BaseAgentEngine, EngineContext
from app.agent_runtime.mcp._transport import ACPRunnerConfig, managed_acp_transport
from app.core.config import settings


class CodexEngine(BaseAgentEngine):
    async def run(
        self,
        *,
        ctx: EngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        if tool_executor is None:
            raise ValueError("Codex engine requires tool_executor")
        trace = getattr(req, "trace", None)

        codex_command = str(getattr(settings, "acp_codex_command", "") or "npx -y @zed-industries/codex-acp")
        cwd = str((getattr(req, "runtime_context", None) or {}).get("project_code_cwd", "."))

        cfg = ACPRunnerConfig(
            provider_type="codex",
            command=codex_command,
            cwd=cwd,
        )

        async with managed_acp_transport(cfg) as transport:
            system_prompt = str(getattr(req, "system_prompt", "") or "")
            user_prompt = str(getattr(req, "input_text", ""))

            if trace:
                trace.emit("llm.request", {"input_preview": user_prompt[:500], "system_preview": system_prompt[:300], "engine": "codex"})

            await transport.send_request({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"systemPrompt": system_prompt},
                "id": 1,
            })

            result = await transport.send_request({
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {"userPrompt": user_prompt},
                "id": 2,
            })

        final_text = str(result.get("result", {}).get("text", ""))
        updates = result.get("result", {}).get("updates", [])
        if trace:
            trace.emit("llm.response", {"text_preview": final_text[:800], "engine": "codex", "updates_count": len(updates)})

        return final_text, {
            "engine": "acp",
            "provider_type": "codex",
            "updates": updates[:20],
        }
