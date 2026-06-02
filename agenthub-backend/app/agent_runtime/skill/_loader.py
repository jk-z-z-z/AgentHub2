from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentscope.skill import LocalSkillLoader

from app.core.config import settings
from app.services.storage_paths import agent_dir


def _get_skills_json_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "skills.json"


def _ensure_default_skills_config(agent_id: int) -> Path:
    p = _get_skills_json_path(agent_id)
    if not p.exists() or not p.read_text(encoding="utf-8").strip():
        p.write_text(
            json.dumps(
                {
                    "enable_agent_local_skills": True,
                    "pool_skill_codes": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return p


def _load_normalized_skills_config(agent_id: int) -> dict[str, Any]:
    _ensure_default_skills_config(int(agent_id))
    raw_path = _get_skills_json_path(int(agent_id))
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8") or "{}")
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    pool_skill_codes = raw.get("pool_skill_codes", [])
    if not isinstance(pool_skill_codes, list):
        pool_skill_codes = []
    normalized_pool = [str(x).strip() for x in pool_skill_codes if isinstance(x, str) and str(x).strip()]
    return {
        "enable_agent_local_skills": bool(raw.get("enable_agent_local_skills", True)),
        "pool_skill_codes": normalized_pool,
    }


def _pool_root() -> Path:
    p = Path(settings.skill_pool_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_skill_loaders_for_agent(agent_id: int) -> list[LocalSkillLoader]:
    cfg = _load_normalized_skills_config(int(agent_id))
    dirs: list[tuple[str, bool]] = []

    pool_root = _pool_root()
    for code in cfg.get("pool_skill_codes", []):
        skill_dir = (pool_root / str(code)).resolve()
        if not skill_dir.exists() or not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        dirs.append((skill_dir.as_posix(), False))

    if bool(cfg.get("enable_agent_local_skills", True)):
        local_dir = (agent_dir(int(agent_id)) / "skills").resolve()
        local_dir.mkdir(parents=True, exist_ok=True)
        dirs.append((local_dir.as_posix(), True))

    unique: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for d, scan_subdir in dirs:
        if d in seen:
            continue
        seen.add(d)
        unique.append((d, scan_subdir))

    return [
        LocalSkillLoader(directory=directory, scan_subdir=scan_subdir)
        for directory, scan_subdir in unique
    ]
