from __future__ import annotations

from typing import Any

from agentscope.agent import Agent
from agentscope.agent import ReActConfig
from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionMode

from app.core.config import settings
from app.event_runtime.types import MessageEventType
from app.manager_runtime.engine.base import BaseManagerEngine, ManagerEngineContext


def _text_content(text: Any) -> list[Any]:
    if isinstance(text, list):
        return text
    return [{"type": "text", "text": str(text or "")}]


class ManagerAgentScopeReactEngine(BaseManagerEngine):
    async def run(
        self,
        *,
        ctx: ManagerEngineContext,
        req: Any,
        tool_executor: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        _ = tool_executor
        cred = OpenAICredential(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        model = OpenAIChatModel(
            credential=cred,
            model=settings.openai_model,
        )
        agent = Agent(
            name=f"manager-react-agent-{ctx.group_id}",
            system_prompt=str(getattr(req, "system_prompt", "") or ""),
            model=model,
            toolkit=getattr(req, "toolkit", None),
            react_config=ReActConfig(max_iters=max(8, int(settings.manager_react_max_iters or 60))),
        )
        try:
            agent.state.permission_context.mode = PermissionMode.BYPASS
        except Exception:
            pass

        messages: list[Msg] = []
        for item in getattr(req, "short_term_memory", None) or []:
            role = str(item.get("role", "user"))
            content = item.get("content", "")
            messages.append(Msg(role=role, content=_text_content(content), name=role))

        input_text = str(getattr(req, "input_text", "") or "")
        messages.append(Msg(role="user", content=_text_content(input_text), name="user"))

        trace = getattr(req, "trace", None)
        if trace:
            trace.emit(
                MessageEventType.Execution.LLM_REQUEST,
                {
                    "input_preview": input_text[:500],
                    "system_preview": str(getattr(req, "system_prompt", "") or "")[:300],
                },
            )
        reply = await agent.reply(messages)
        parts: list[str] = []
        for part in reply.content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text") or ""))
            elif getattr(part, "type", None) == "text":
                parts.append(str(getattr(part, "text", "") or ""))
            elif isinstance(part, str):
                parts.append(part)
        text = "".join(parts).strip()
        if trace:
            trace.emit(MessageEventType.Execution.LLM_RESPONSE, {"text_preview": text[:800]})
        return text, {"engine": "agentscope_react"}
