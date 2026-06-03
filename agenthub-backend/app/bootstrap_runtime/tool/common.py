from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

from app.common.file_utils import normalize_rel_path, safe_resolve_under_root
from app.services.storage_init_service import ensure_agent_space
from app.services.storage_paths import agent_dir


def agent_root(agent_id: int) -> Path:
    ensure_agent_space(int(agent_id))
    return agent_dir(int(agent_id)).resolve()


def safe_resolve_under_agent(agent_id: int, rel_path: str) -> Path:
    root = agent_root(agent_id)
    rel = normalize_rel_path(rel_path)
    target = safe_resolve_under_root(root, rel)
    if target == root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="path must point to a file or subdirectory")
    return target
