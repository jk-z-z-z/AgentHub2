from __future__ import annotations

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionMode

from app.core.config import settings
from app.agent_runtime.toolkit_builder import build_toolkit_for_agent


async def internal_llm_chat(
    message: str,
    *,
    system_prompt: str | None = None,
    agent_instance_id: int | None = None,
    runtime_context: dict | None = None,
    short_term_messages: list[Msg] | None = None,
) -> str:
    if not settings.openai_api_key:
        return (
            "Missing model credentials. Set AGENTHUB_OPENAI_API_KEY (and optionally "
            "AGENTHUB_OPENAI_BASE_URL / AGENTHUB_OPENAI_MODEL) in .env."
        )
    cred = OpenAICredential(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    model = OpenAIChatModel(credential=cred, model=settings.openai_model, stream=False)
    toolkit = build_toolkit_for_agent(agent_instance_id, runtime_context=runtime_context)
    agent = Agent(
        name="agenthub-internal-llm",
        system_prompt=system_prompt or settings.default_ai_system_prompt,
        model=model,
        toolkit=toolkit,
    )
    agent.state.permission_context.mode = PermissionMode.BYPASS
    base_user_msg = Msg(name="user", role="user", content=[{"type": "text", "text": message}])
    history = list(short_term_messages or [])
    history.append(base_user_msg)
    reply = await agent.reply(history)

    parts: list[str] = []
    for part in reply.content:
        if isinstance(part, dict):
            if part.get("type") == "text":
                parts.append(str(part.get("text", "")))
            continue
        part_type = getattr(part, "type", None)
        if part_type == "text":
            parts.append(str(getattr(part, "text", "")))
    return "".join(parts).strip()

