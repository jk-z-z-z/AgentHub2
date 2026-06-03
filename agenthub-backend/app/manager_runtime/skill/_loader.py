from __future__ import annotations

from pathlib import Path
from typing import Any

from agentscope.skill import LocalSkillLoader

from app.services.storage_paths import project_dir


def _builtin_skill_root() -> Path:
    return (Path(__file__).resolve().parent / "builtin").resolve()


def _local_skill_root(group_id: int) -> Path:
    root = (project_dir(int(group_id)) / "manager_skills").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _iter_skill_dirs(group_id: int) -> list[tuple[Path, bool]]:
    dirs: list[tuple[Path, bool]] = []
    builtin_root = _builtin_skill_root()
    if builtin_root.exists() and builtin_root.is_dir():
        dirs.append((builtin_root, True))
    local_root = _local_skill_root(int(group_id))
    if local_root.exists() and local_root.is_dir():
        dirs.append((local_root, True))
    return dirs


def load_manager_skill_loaders(group_id: int) -> list[LocalSkillLoader]:
    return [
        LocalSkillLoader(directory=directory.as_posix(), scan_subdir=scan_subdir)
        for directory, scan_subdir in _iter_skill_dirs(int(group_id))
    ]


def load_manager_skill_prompt_sections(group_id: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for root, scan_subdir in _iter_skill_dirs(int(group_id)):
        candidates = sorted(root.rglob("SKILL.md")) if scan_subdir else [root / "SKILL.md"]
        for path in candidates:
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8").strip()
            except Exception:
                text = ""
            if not text:
                continue
            items.append({"name": path.parent.name, "content": text})
    return items
