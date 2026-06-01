from __future__ import annotations

import json
from datetime import datetime, timezone

from app.services import storage_paths as sp


def ensure_user_space(user_id: int) -> None:
    root = sp.user_dir(user_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "knowledge").mkdir(parents=True, exist_ok=True)
    (root / "PROFILE.md").touch(exist_ok=True)
    (root / "MEMORY.md").touch(exist_ok=True)


def ensure_project_space(project_id: int) -> None:
    root = sp.project_dir(project_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "knowledge").mkdir(parents=True, exist_ok=True)
    (root / "shared" / "code").mkdir(parents=True, exist_ok=True)
    (root / "PROFILE.md").touch(exist_ok=True)
    (root / "MEMORY.md").touch(exist_ok=True)


def ensure_personal_group_space(group_id: int) -> None:
    """
    personal group uses the same projects/{group-id} root for now,
    but does not require shared/code initialization.
    """
    root = sp.project_dir(group_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "knowledge").mkdir(parents=True, exist_ok=True)
    (root / "PROFILE.md").touch(exist_ok=True)
    (root / "MEMORY.md").touch(exist_ok=True)


def ensure_agent_space(agent_id: int, soul_md: str | None = None, profile_md: str | None = None) -> None:
    root = sp.agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    (root / "mcps").mkdir(parents=True, exist_ok=True)
    (root / "knowledge").mkdir(parents=True, exist_ok=True)
    soul_path = root / "SOUL.md"
    if not soul_path.exists():
        soul_path.write_text(soul_md or "", encoding="utf-8")
    profile_path = root / "PROFILE.md"
    if not profile_path.exists():
        profile_path.write_text(profile_md or "", encoding="utf-8")
    (root / "BOOTSTRAP.md").touch(exist_ok=True)
    (root / "MEMORY.md").touch(exist_ok=True)
    (root / "tools.json").touch(exist_ok=True)
    (root / "skills.json").touch(exist_ok=True)


def ensure_runtime_personal(agent_id: int, user_id: int) -> None:
    root = sp.runtime_personal_dir(agent_id, user_id)
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    session_path = root / "session.json"
    if not session_path.exists():
        session_path.write_text(
            json.dumps(
                {
                    "agent_id": str(agent_id),
                    "user_id": str(user_id),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def ensure_runtime_project(agent_id: int, project_id: int) -> None:
    root = sp.runtime_project_dir(agent_id, project_id)
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    session_path = root / "session.json"
    if not session_path.exists():
        session_path.write_text(
            json.dumps(
                {
                    "agent_id": str(agent_id),
                    "project_id": str(project_id),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
