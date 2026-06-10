from __future__ import annotations

from pathlib import Path
from typing import Any

from agentscope.skill import LocalSkillLoader

from app.services.storage_paths import project_dir


def _builtin_skill_root() -> Path:
    return (Path(__file__).resolve().parent / "builtin").resolve()


def _local_skill_root(group_id: int) -> Path:
    return (project_dir(int(group_id)) / "manager_skills").resolve()


def _has_skill_files(root: Path, *, scan_subdir: bool) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    if (root / "SKILL.md").exists():
        return True
    if not scan_subdir:
        return False
    return any(path.is_file() for path in root.rglob("SKILL.md"))


def _iter_skill_dirs(group_id: int) -> list[tuple[Path, bool]]:
    dirs: list[tuple[Path, bool]] = []
    builtin_root = _builtin_skill_root()
    if _has_skill_files(builtin_root, scan_subdir=True):
        dirs.append((builtin_root, True))
    local_root = _local_skill_root(int(group_id))
    if _has_skill_files(local_root, scan_subdir=True):
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
