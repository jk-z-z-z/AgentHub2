from __future__ import annotations

import json

from app.models.agent_profile import AgentProfile


PROFILE_FILE_MAP: dict[str, str] = {
    "AGENTS.md": "agents_md",
    "PROFILE.md": "profile_md",
    "SOUL.md": "soul_md",
    "BOOTSTRAP.md": "bootstrap_md",
    "MEMORY.md": "memory_md",
    "HEARTBEAT.md": "heartbeat_md",
}


def get_profile_enabled_files(profile: AgentProfile) -> dict[str, bool]:
    try:
        data = json.loads(profile.enabled_files_json or "{}")
        if isinstance(data, dict):
            return {k: bool(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def set_profile_enabled_files(profile: AgentProfile, enabled_files: dict[str, bool]) -> None:
    profile.enabled_files_json = json.dumps(enabled_files, ensure_ascii=False)


def get_profile_file_content(profile: AgentProfile, filename: str) -> str:
    if filename not in PROFILE_FILE_MAP:
        raise ValueError(f"Unsupported filename: {filename}")
    return getattr(profile, PROFILE_FILE_MAP[filename]) or ""


def set_profile_file_content(profile: AgentProfile, filename: str, content: str) -> None:
    if filename not in PROFILE_FILE_MAP:
        raise ValueError(f"Unsupported filename: {filename}")
    setattr(profile, PROFILE_FILE_MAP[filename], content or "")

