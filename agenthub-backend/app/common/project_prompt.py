from __future__ import annotations

from pathlib import Path

from app.services.storage_init_service import ensure_project_space, ensure_runtime_project
from app.services.storage_paths import agent_dir, project_dir


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def build_project_system_prompt(*, agent_id: int, project_id: int) -> str:
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
