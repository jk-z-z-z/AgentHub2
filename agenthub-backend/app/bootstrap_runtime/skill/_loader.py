from __future__ import annotations

from pathlib import Path

from agentscope.skill import LocalSkillLoader


def _builtin_skill_root() -> Path:
    return (Path(__file__).resolve().parent / "builtin").resolve()


def load_bootstrap_skill_loaders() -> list[LocalSkillLoader]:
    root = _builtin_skill_root()
    if not root.exists() or not root.is_dir():
        return []
    return [LocalSkillLoader(directory=root.as_posix(), scan_subdir=True)]
