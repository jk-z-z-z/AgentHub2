from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.schemas.common import ApiResponse


router = APIRouter(prefix="/ai", tags=["ai"])


def _text_content(text: Any) -> list[Any]:
    if isinstance(text, list):
        return text
    return [{"type": "text", "text": str(text or "")}]


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", "user"))
    return str(getattr(message, "role", "user"))


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "")


def _extract_response_text(response: Any) -> str:
    parts = getattr(response, "content", None) or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
        elif getattr(part, "type", None) == "text":
            texts.append(str(getattr(part, "text", "") or ""))
    return "".join(texts).strip()


async def _chat(user_prompt: str, system_prompt: str | None = None, short_term_messages: list | None = None, *, runtime_context: dict | None = None) -> str:
    cred = OpenAICredential(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    model = OpenAIChatModel(credential=cred, model=settings.openai_model, stream=False)
    messages: list[Msg] = []
    if system_prompt:
        messages.append(Msg(role="system", content=_text_content(system_prompt), name="system"))
    for message in short_term_messages or []:
        role = _message_role(message)
        messages.append(Msg(role=role, content=_text_content(_message_content(message)), name=role))
    if runtime_context:
        messages.append(Msg(role="system", content=_text_content(f"runtime_context={runtime_context}"), name="runtime_context"))
    messages.append(Msg(role="user", content=_text_content(user_prompt), name="user"))
    response = await model(messages)
    return _extract_response_text(response)


@router.post("/chat", response_model=ApiResponse[AIChatResponse])
async def ai_chat_api(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
):
    _ = db
    reply = await _chat(
        payload.message,
        system_prompt=payload.system_prompt,
        runtime_context=payload.runtime_context or None,
    )
    return ApiResponse(data=AIChatResponse(reply=reply))
