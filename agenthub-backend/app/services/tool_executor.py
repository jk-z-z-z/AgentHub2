from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.common.file_utils import list_dir_entries, normalize_rel_path, safe_resolve_under_root, write_text
from app.core.config import settings
from app.services.storage_init_service import (
    ensure_agent_space,
    ensure_project_space,
    ensure_runtime_personal,
    ensure_runtime_project,
    ensure_user_space,
)
from app.services.project_code_service import get_project_code_root, list_project_code_fs, read_project_code_file, safe_project_code_path
from app.services.storage_paths import agent_dir, project_dir, runtime_personal_dir, runtime_project_dir, user_dir


ALLOWED_FILE_TOOL_ROOTS: set[str] = {"knowledge", "skills", "mcps"}
ALLOWED_AGENT_SPEC_FILES: set[str] = {"SOUL.md", "AGENTS.md", "PROFILE.md", "BOOTSTRAP.md", "MEMORY.md", "HEARTBEAT.md"}
ALLOWED_PROJECT_COMMANDS: set[str] = {
    "npm run type-check",
    "npm run build",
    "pnpm run type-check",
    "pnpm run build",
    "yarn type-check",
    "yarn build",
}


def _safe_resolve_under_agent(agent_id: int, rel_path: str) -> Path:
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

def _resolve_worker_root(agent_id: int, scope: str, runtime_context: dict | None) -> Path:
    group_type = _runtime_str(runtime_context, "group_type")
    group_id = _runtime_int(runtime_context, "group_id")
    user_id = _runtime_int(runtime_context, "user_id")

    if scope == "project_code":
        if group_type != "project" or not group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_code scope requires project group context")
        ensure_project_space(group_id)
        return (project_dir(group_id) / "shared" / "code").resolve()
    if scope == "runtime_workspace":
        if group_type == "project" and group_id:
            ensure_runtime_project(agent_id, group_id)
            return (runtime_project_dir(agent_id, group_id) / "workspace" / "code").resolve()
        if group_type == "personal" and user_id:
            ensure_runtime_personal(agent_id, user_id)
            return (runtime_personal_dir(agent_id, user_id) / "workspace" / "code").resolve()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="runtime_workspace scope requires valid conversation context")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope must be project_code or runtime_workspace")


def _runtime_int(context: dict | None, key: str) -> int | None:
    if not isinstance(context, dict):
        return None
    value = context.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_str(context: dict | None, key: str) -> str | None:
    if not isinstance(context, dict):
        return None
    value = context.get(key)
    if value in (None, ""):
        return None
    return str(value)


def execute_builtin_tool(*, agent_id: int, tool_code: str, args: dict, runtime_context: dict | None = None) -> dict:
    ensure_agent_space(agent_id)

    if tool_code == "file_list":
        rel_dir = str(args.get("dir") or "knowledge")
        p = _safe_resolve_under_agent(agent_id, rel_dir)
        if not p.exists():
            return {"entries": []}
        if not p.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dir is not a directory")
        entries = []
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            entries.append(
                {
                    "name": child.name,
                    "path": child.relative_to(agent_dir(agent_id)).as_posix(),
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else 0,
                }
            )
        return {"entries": entries}

    if tool_code == "file_read":
        rel_path = str(args.get("path") or "")
        p = _safe_resolve_under_agent(agent_id, rel_path)
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return {"path": p.relative_to(agent_dir(agent_id)).as_posix(), "content": p.read_text(encoding="utf-8")}

    if tool_code == "file_write":
        rel_path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        p = _safe_resolve_under_agent(agent_id, rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": p.relative_to(agent_dir(agent_id)).as_posix(), "written": True, "size": len(content)}

    if tool_code == "project_code_list":
        group_type = _runtime_str(runtime_context, "group_type")
        group_id = _runtime_int(runtime_context, "group_id")
        if group_type != "project" or not group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_code_list requires project group context")
        rel_dir = str(args.get("dir") or "").strip()
        root = get_project_code_root(group_id)
        target = root if not rel_dir else safe_project_code_path(group_id, rel_dir)
        if not target.exists():
            return {"entries": []}
        if not target.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dir is not a directory")
        if target == root:
            return {"entries": list_project_code_fs(group_id)}
        entries = []
        for child in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            rel = child.relative_to(root).as_posix()
            entries.append({"name": child.name, "path": f"{rel}/" if child.is_dir() else rel, "is_dir": child.is_dir(), "size": child.stat().st_size if child.is_file() else 0})
        return {"entries": entries}

    if tool_code == "project_code_read":
        group_type = _runtime_str(runtime_context, "group_type")
        group_id = _runtime_int(runtime_context, "group_id")
        if group_type != "project" or not group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_code_read requires project group context")
        rel_path = str(args.get("path") or "")
        content = read_project_code_file(group_id, rel_path)
        return {"path": normalize_rel_path(rel_path), "content": content}

    if tool_code == "worker_file_list":
        scope = str(args.get("scope") or "")
        rel_dir = str(args.get("dir") or "").strip()
        root = _resolve_worker_root(agent_id, scope, runtime_context)
        root.mkdir(parents=True, exist_ok=True)
        target = root if not rel_dir else safe_resolve_under_root(root, rel_dir)
        if not target.exists():
            return {"entries": []}
        if not target.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dir is not a directory")
        return {"entries": list_dir_entries(root, target)}

    if tool_code == "worker_file_read":
        scope = str(args.get("scope") or "")
        rel_path = str(args.get("path") or "")
        root = _resolve_worker_root(agent_id, scope, runtime_context)
        root.mkdir(parents=True, exist_ok=True)
        target = safe_resolve_under_root(root, rel_path)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return {"path": target.relative_to(root).as_posix(), "scope": scope, "content": target.read_text(encoding="utf-8")}

    if tool_code == "user_profile_write":
        user_id = _runtime_int(runtime_context, "user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_profile_write requires runtime user context")
        ensure_user_space(user_id)
        content = str(args.get("content") or "")
        mode = str(args.get("mode") or "overwrite")
        path = user_dir(user_id) / "PROFILE.md"
        write_text(path, content, mode)
        return {"path": path.as_posix(), "written": True, "mode": mode}

    if tool_code == "agent_spec_write":
        filename = str(args.get("filename") or "")
        if filename not in ALLOWED_AGENT_SPEC_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"filename must be one of: {', '.join(sorted(ALLOWED_AGENT_SPEC_FILES))}",
            )
        content = str(args.get("content") or "")
        mode = str(args.get("mode") or "overwrite")
        path = agent_dir(agent_id) / filename
        write_text(path, content, mode)
        return {"path": path.relative_to(agent_dir(agent_id)).as_posix(), "written": True, "mode": mode}

    if tool_code == "worker_file_write":
        scope = str(args.get("scope") or "runtime_workspace")
        rel_path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        mode = str(args.get("mode") or "overwrite")

        root = _resolve_worker_root(agent_id, scope, runtime_context)
        root.mkdir(parents=True, exist_ok=True)
        target = safe_resolve_under_root(root, rel_path)
        write_text(target, content, mode)
        return {"path": target.relative_to(root).as_posix(), "scope": scope, "written": True, "mode": mode}

    if tool_code == "project_command_run":
        group_type = _runtime_str(runtime_context, "group_type")
        group_id = _runtime_int(runtime_context, "group_id")
        if group_type != "project" or not group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_command_run requires project group context")
        command = str(args.get("command") or "").strip()
        if command not in ALLOWED_PROJECT_COMMANDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"command must be one of: {', '.join(sorted(ALLOWED_PROJECT_COMMANDS))}",
            )
        root = get_project_code_root(group_id)
        proc = subprocess.run(
            command,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=max(10, int(settings.project_command_timeout_seconds)),
        )
        return {
            "command": command,
            "cwd": root.as_posix(),
            "exit_code": int(proc.returncode),
            "stdout": proc.stdout[-20000:],
            "stderr": proc.stderr[-20000:],
            "ok": proc.returncode == 0,
        }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unsupported tool: {tool_code}")
