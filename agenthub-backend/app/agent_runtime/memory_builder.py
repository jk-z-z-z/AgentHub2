from __future__ import annotations

from app.services.agent_workspace_service import load_agent_soul
from app.services.storage_init_service import (
    ensure_project_space,
    ensure_runtime_personal,
    ensure_runtime_project,
    ensure_user_space,
)
from app.services.storage_paths import agent_dir, project_dir, user_dir


def _read_text(p) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def _load_agent_core(*, agent_id: int) -> tuple[str, str]:
    soul = load_agent_soul(agent_id) or ""
    profile_md = _read_text(agent_dir(agent_id) / "PROFILE.md")
    return soul, profile_md


def build_personal_system_prompt(*, agent_id: int, user_id: int) -> str:
    ensure_user_space(user_id)
    ensure_runtime_personal(agent_id, user_id)

    soul, agent_profile_md = _load_agent_core(agent_id=agent_id)
    profile = _read_text(user_dir(user_id) / "PROFILE.md")
    memory = _read_text(user_dir(user_id) / "MEMORY.md")

    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if agent_profile_md.strip():
        parts.append("# Agent PROFILE\n" + agent_profile_md.strip())
    if profile.strip():
        parts.append("# User PROFILE\n" + profile.strip())
    if memory.strip():
        parts.append("# User MEMORY\n" + memory.strip())
    return "\n\n".join(parts).strip()


def build_project_system_prompt(*, agent_id: int, project_id: int) -> str:
    ensure_project_space(project_id)
    ensure_runtime_project(agent_id, project_id)

    soul, agent_profile_md = _load_agent_core(agent_id=agent_id)
    profile = _read_text(project_dir(project_id) / "PROFILE.md")
    memory = _read_text(project_dir(project_id) / "MEMORY.md")

    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if agent_profile_md.strip():
        parts.append("# Agent PROFILE\n" + agent_profile_md.strip())
    if profile.strip():
        parts.append("# Project PROFILE\n" + profile.strip())
    if memory.strip():
        parts.append("# Project MEMORY\n" + memory.strip())
    return "\n\n".join(parts).strip()
