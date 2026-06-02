from __future__ import annotations

from typing import Any

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel

from app.agent_runtime.engine.base import BaseAgentEngine, EngineContext
from app.core.config import settings


def _text_content(text: Any) -> list[Any]:
    if isinstance(text, list):
        return text
    return [{"type": "text", "text": str(text or "")}]


class AgentScopeReactEngine(BaseAgentEngine):
    async def run(
        self,
        *,
        ctx: EngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        cred = OpenAICredential(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        model = OpenAIChatModel(
            credential=cred,
            model=settings.openai_model,
        )

        from agentscope.permission import PermissionMode

        agent = Agent(
            name=f"react-agent-{ctx.agent_id}",
            system_prompt=str(getattr(req, "system_prompt", "") or ""),
            model=model,
            toolkit=getattr(req, "_toolkit", None),
        )

        try:
            agent.state.permission_context.mode = PermissionMode.BYPASS
        except Exception:
            pass

        short_term = getattr(req, "short_term_memory", None) or []
        messages: list[Msg] = []
        for msg in short_term:
            role = str(msg.get("role", "user"))
            content = msg.get("content", "")
            messages.append(Msg(role=role, content=_text_content(content), name=role))

        input_text = str(getattr(req, "input_text", ""))
        messages.append(Msg(role="user", content=_text_content(input_text), name="user"))

        reply = await agent.reply(messages)
        parts: list[str] = []
        for part in reply.content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text") or ""))
            elif getattr(part, "type", None) == "text":
                parts.append(str(getattr(part, "text", "") or ""))
            elif isinstance(part, str):
                parts.append(part)

        return "".join(parts).strip(), {"engine": "agentscope_react"}
