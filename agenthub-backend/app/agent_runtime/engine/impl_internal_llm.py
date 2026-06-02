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
        trace = getattr(req, "trace", None)
        system_prompt = str(getattr(req, "system_prompt", "") or "")
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
        if system_prompt:
            messages.append(
                Msg(
                    role="system",
                    content=_text_content(system_prompt),
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

        if trace:
            trace.emit("llm.request", {"input_preview": input_text[:500], "system_preview": system_prompt[:300]})
        response = await model(messages)
        text = _extract_response_text(response)
        if trace:
            trace.emit("llm.response", {"text_preview": text[:800]})
        return text, {"engine": "internal_llm"}
