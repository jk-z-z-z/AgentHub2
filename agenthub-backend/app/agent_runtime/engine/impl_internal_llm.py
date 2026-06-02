from __future__ import annotations

from typing import Any

from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel

from app.agent_runtime.engine.base import BaseAgentEngine, EngineContext
from app.core.config import settings


def _text_content(text: Any) -> list[Any]:
    if isinstance(text, list):
        return text
    return [{"type": "text", "text": str(text or "")}]


def _extract_response_text(response: Any) -> str:
    parts = getattr(response, "content", None) or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
        elif getattr(part, "type", None) == "text":
            texts.append(str(getattr(part, "text", "") or ""))
    return "".join(texts).strip()


class InternalLLMEngine(BaseAgentEngine):
    async def run(
        self,
        *,
        ctx: EngineContext,
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
            stream=False,
        )

        messages: list[Msg] = []
        if str(getattr(req, "system_prompt", "")):
            messages.append(
                Msg(
                    role="system",
                    content=_text_content(str(getattr(req, "system_prompt", ""))),
                    name="system",
                )
            )

        short_term = getattr(req, "short_term_memory", None) or []
        for msg in short_term:
            role = str(msg.get("role", "user"))
            content = msg.get("content", "")
            messages.append(Msg(role=role, content=_text_content(content), name=role))

        input_text = str(getattr(req, "input_text", ""))
        messages.append(Msg(role="user", content=_text_content(input_text), name="user"))

        response = await model(messages)
        return _extract_response_text(response), {"engine": "internal_llm"}
