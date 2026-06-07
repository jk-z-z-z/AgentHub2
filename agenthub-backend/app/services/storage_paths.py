from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    return Path(settings.data_root).expanduser().resolve()


def agents_root() -> Path:
    return _root() / "agents"


def users_root() -> Path:
    return _root() / "users"


def projects_root() -> Path:
    return _root() / "projects"


def runtime_root() -> Path:
    return _root() / "runtime"


def workspaces_root() -> Path:
    return _root() / "workspaces"


def agent_dir(agent_id: int) -> Path:
    return agents_root() / str(agent_id)


def user_dir(user_id: int) -> Path:
    return users_root() / str(user_id)


def project_dir(project_id: int) -> Path:
    return projects_root() / str(project_id)


def runtime_personal_dir(agent_id: int, user_id: int) -> Path:
    return runtime_root() / "personal" / f"{agent_id}@{user_id}"


def runtime_project_dir(agent_id: int, project_id: int) -> Path:
    return runtime_root() / "project" / f"{agent_id}@{project_id}"


def workspace_meta_dir(workspace_id: int) -> Path:
    return workspaces_root() / str(workspace_id)


def workspace_snapshots_dir(workspace_id: int) -> Path:
    return workspace_meta_dir(workspace_id) / "snapshots"


def sandbox_runs_root() -> Path:
    return runtime_root() / "sandboxes"


def sandbox_run_dir(sandbox_id: str) -> Path:
    return sandbox_runs_root() / str(sandbox_id)
