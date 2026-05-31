from __future__ import annotations

from app.services.storage_init_service import ensure_agent_space
from app.services.storage_paths import agent_dir


def ensure_agent_workspace(*args, **kwargs):
    raise RuntimeError("ensure_agent_workspace is deprecated; use storage_init_service.ensure_agent_space()")


def get_agent_workspace_path(agent_instance_id: int):
    return agent_dir(agent_instance_id)


def load_agent_soul(agent_instance_id: int) -> str | None:
    soul_path = agent_dir(agent_instance_id) / "SOUL.md"
    if not soul_path.exists():
        return None
    text = soul_path.read_text(encoding="utf-8").strip()
    return text or None


def save_agent_soul(agent_instance_id: int, soul_md: str) -> None:
    ensure_agent_space(agent_instance_id, soul_md=soul_md)
