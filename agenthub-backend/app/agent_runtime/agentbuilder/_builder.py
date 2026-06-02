from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentscope.tool import Toolkit
from sqlalchemy.orm import Session

from app.agent_runtime.engine.base import EngineContext
from app.agent_runtime.skill._loader import load_skill_loaders_for_agent
from app.agent_runtime.tool._loader import load_toolkit_for_agent
from app.models.agent_instance import AgentInstance
from app.services.storage_init_service import (
    ensure_project_space,
    ensure_runtime_personal,
    ensure_runtime_project,
    ensure_user_space,
)
from app.services.storage_paths import agent_dir, project_dir, user_dir


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def _build_system_prompt_personal(*, agent_id: int, user_id: int) -> str:
    ensure_user_space(int(user_id))
    ensure_runtime_personal(int(agent_id), int(user_id))

    soul = _read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    user_profile = _read_text(user_dir(int(user_id)) / "PROFILE.md")
    user_memory = _read_text(user_dir(int(user_id)) / "MEMORY.md")

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


def _build_system_prompt_project(*, agent_id: int, project_id: int) -> str:
    ensure_project_space(int(project_id))
    ensure_runtime_project(int(agent_id), int(project_id))

    soul = _read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    project_profile = _read_text(project_dir(int(project_id)) / "PROFILE.md")
    project_memory = _read_text(project_dir(int(project_id)) / "MEMORY.md")

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


@dataclass
class BuiltAgent:
    agent_instance: AgentInstance
    system_prompt: str
    toolkit: Toolkit
    skill_loaders: list[Any]
    engine_ctx: EngineContext


def build_complete_agent(
    db: Session,
    *,
    agent_id: int,
    extra_context: dict[str, Any],
    runtime_context: dict[str, Any] | None = None,
    trace: Any | None = None,
) -> BuiltAgent:
    agent_instance = db.query(AgentInstance).filter(AgentInstance.id == int(agent_id)).first()
    if not agent_instance:
        raise ValueError(f"Agent instance not found: {agent_id}")

    user_id = extra_context.get("user_id")
    project_id = extra_context.get("project_id")

    system_prompt: str
    if project_id is not None:
        system_prompt = _build_system_prompt_project(agent_id=int(agent_id), project_id=int(project_id))
    elif user_id is not None:
        system_prompt = _build_system_prompt_personal(agent_id=int(agent_id), user_id=int(user_id))
    else:
        system_prompt = ""

    toolkit = load_toolkit_for_agent(int(agent_id), runtime_context=runtime_context, trace=trace)
    skill_loaders = load_skill_loaders_for_agent(int(agent_id))

    engine_type = str(getattr(agent_instance, "engine_type", "internal_llm") or "internal_llm")
    engine_cfg = str(getattr(agent_instance, "engine_config_json", "{}") or "{}")
    engine_ctx = EngineContext(
        agent_id=int(agent_id),
        engine_type=engine_type,
        engine_config_json=engine_cfg,
    )

    return BuiltAgent(
        agent_instance=agent_instance,
        system_prompt=system_prompt,
        toolkit=toolkit,
        skill_loaders=skill_loaders,
        engine_ctx=engine_ctx,
    )
