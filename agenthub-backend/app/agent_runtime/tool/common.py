from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

from app.common.file_utils import normalize_rel_path, safe_resolve_under_root
from app.services.storage_init_service import (
    ensure_project_space,
    ensure_runtime_personal,
    ensure_runtime_project,
    ensure_user_space,
)
from app.services.storage_paths import agent_dir, project_dir, runtime_personal_dir, runtime_project_dir, user_dir


ALLOWED_FILE_TOOL_ROOTS: set[str] = {"knowledge", "skills", "mcps"}


def safe_resolve_under_agent(agent_id: int, rel_path: str) -> Path:
    root = agent_dir(agent_id).resolve()
    rel = normalize_rel_path(rel_path)
    parts = rel.split("/", 1)
    top = parts[0]
    if top not in ALLOWED_FILE_TOOL_ROOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path must be under one of: {', '.join(sorted(ALLOWED_FILE_TOOL_ROOTS))}",
        )
    full = (root / rel).resolve()
    if root not in full.parents and full != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path escapes agent workspace")
    return full


def runtime_int(context: dict | None, key: str) -> int | None:
    if not isinstance(context, dict):
        return None
    value = context.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def runtime_str(context: dict | None, key: str) -> str | None:
    if not isinstance(context, dict):
        return None
    value = context.get(key)
    if value in (None, ""):
        return None
    return str(value)


def mark_read(runtime_context: dict | None, path: str) -> None:
    if not isinstance(runtime_context, dict):
        return
    seen = runtime_context.get("__fs_read_paths")
    if not isinstance(seen, list):
        seen = []
        runtime_context["__fs_read_paths"] = seen
    if path not in seen:
        seen.append(path)


def was_read(runtime_context: dict | None, path: str) -> bool:
    if not isinstance(runtime_context, dict):
        return False
    seen = runtime_context.get("__fs_read_paths")
    return isinstance(seen, list) and path in seen


def require_project_group(runtime_context: dict | None) -> int:
    group_type = runtime_str(runtime_context, "group_type")
    group_id = runtime_int(runtime_context, "group_id") or runtime_int(runtime_context, "project_id")
    if group_type not in {None, "", "project"} or not group_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requires project group context")
    ensure_project_space(group_id)
    return int(group_id)


def require_user(runtime_context: dict | None) -> int:
    user_id = runtime_int(runtime_context, "user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requires runtime user context")
    ensure_user_space(user_id)
    return int(user_id)


def project_code_root(group_id: int) -> Path:
    root = (project_dir(group_id) / "shared" / "code").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_worker_root(agent_id: int, scope: str, runtime_context: dict | None) -> Path:
    group_type = runtime_str(runtime_context, "group_type")
    group_id = runtime_int(runtime_context, "group_id")
    user_id = runtime_int(runtime_context, "user_id")

    if scope == "project_code":
        if group_type != "project" or not group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_code scope requires project group context")
        ensure_project_space(group_id)
        return (project_dir(group_id) / "shared" / "code").resolve()
    if scope == "runtime_workspace":
        if group_type == "project" and group_id:
            ensure_runtime_project(agent_id, group_id)
            return (runtime_project_dir(agent_id, group_id) / "workspace").resolve()
        if group_type == "personal" and user_id:
            ensure_runtime_personal(agent_id, user_id)
            return (runtime_personal_dir(agent_id, user_id) / "workspace").resolve()
        # fallback: allow a per-agent local runtime
        return (agent_dir(agent_id) / "runtime").resolve()

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported scope")


def user_profile_path(user_id: int) -> Path:
    return user_dir(user_id) / "PROFILE.md"


def agent_profile_path(agent_id: int) -> Path:
    return agent_dir(agent_id) / "PROFILE.md"


def safe_resolve_under(root: Path, rel: str) -> Path:
    root = root.resolve()
    target = safe_resolve_under_root(root, rel)
    return target
