"""完全零依赖的AI辅助函数，打破所有循环导入。

不引用任何service层的其他东西，从根源上消除循环依赖。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from sqlalchemy.orm import Session

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


async def simple_internal_llm_chat(
    user_prompt: str,
    system_prompt: str | None = None,
    short_term_messages: list | None = None,
) -> str:
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
        messages.append(Msg(role="system", content=_text_content(system_prompt), name="system"))
    for m in (short_term_messages or []):
        messages.append(
            Msg(
                role=str(m.get("role", "user")),
                content=_text_content(m.get("content", "")),
                name=str(m.get("role", "user")),
            )
        )
    messages.append(Msg(role="user", content=_text_content(user_prompt), name="user"))
    resp = await model(messages)
    return _extract_response_text(resp)


def _simple_read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def build_personal_system_prompt(*, agent_id: int, user_id: int) -> str:
    from app.services.storage_paths import agent_dir, user_dir
    from app.services.storage_init_service import ensure_user_space, ensure_runtime_personal

    ensure_user_space(int(user_id))
    ensure_runtime_personal(int(agent_id), int(user_id))
    soul = _simple_read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _simple_read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    user_profile = _simple_read_text(user_dir(int(user_id)) / "PROFILE.md")
    user_memory = _simple_read_text(user_dir(int(user_id)) / "MEMORY.md")
    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if profile_md.strip():
        parts.append("# Agent PROFILE\n" + profile_md.strip())
    if user_profile.strip():
        parts.append("# User PROFILE\n" + user_profile.strip())
    if user_memory.strip():
        parts.append("# User MEMORY\n" + user_memory.strip())
    return "\n\n".join(parts).strip()


def build_project_system_prompt(*, agent_id: int, project_id: int) -> str:
    from app.services.storage_paths import agent_dir, project_dir
    from app.services.storage_init_service import ensure_project_space, ensure_runtime_project

    ensure_project_space(int(project_id))
    ensure_runtime_project(int(agent_id), int(project_id))
    soul = _simple_read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _simple_read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    project_profile = _simple_read_text(project_dir(int(project_id)) / "PROFILE.md")
    project_memory = _simple_read_text(project_dir(int(project_id)) / "MEMORY.md")
    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if profile_md.strip():
        parts.append("# Agent PROFILE\n" + profile_md.strip())
    if project_profile.strip():
        parts.append("# Project PROFILE\n" + project_profile.strip())
    if project_memory.strip():
        parts.append("# Project MEMORY\n" + project_memory.strip())
    return "\n\n".join(parts).strip()


def build_bootstrap_system_prompt(*, agent_id: int, user_id: int) -> str:
    from app.services.storage_paths import agent_dir, user_dir
    from app.services.storage_init_service import ensure_user_space, ensure_runtime_personal

    ensure_user_space(int(user_id))
    ensure_runtime_personal(int(agent_id), int(user_id))
    soul = _simple_read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _simple_read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    bootstrap = _simple_read_text(agent_dir(int(agent_id)) / "BOOTSTRAP.md")
    user_profile = _simple_read_text(user_dir(int(user_id)) / "PROFILE.md")
    user_memory = _simple_read_text(user_dir(int(user_id)) / "MEMORY.md")
    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if profile_md.strip():
        parts.append("# Agent PROFILE\n" + profile_md.strip())
    if bootstrap.strip():
        parts.append("# Agent BOOTSTRAP\n" + bootstrap.strip())
    parts.append(
        "# Bootstrap Rules\n"
        "你正在为当前智能体进行“初始化定义（bootstrap）”。你的目标是：\n"
        "- 按 BOOTSTRAP.md 的规范逐步向用户提问，收集缺失信息。\n"
        "- 用工具更新智能体工作区中的配置文件（例如 PROFILE.md、tools.json、skills.json、knowledge/*）。\n"
        "- 当你认为信息已足够，向用户询问是否结束 bootstrap。\n"
        "- 用户确认结束后，删除本智能体工作区中的 BOOTSTRAP.md，并提示用户 bootstrap 已完成。\n"
        "注意：不要一次性抛出过多问题，优先问最关键的 1-3 个。\n"
    )
    if user_profile.strip():
        parts.append("# User PROFILE\n" + user_profile.strip())
    if user_memory.strip():
        parts.append("# User MEMORY\n" + user_memory.strip())
    return "\n\n".join(parts).strip()
