from __future__ import annotations

import json
from pathlib import Path

import frontmatter

from app.core.config import settings
from app.services.storage_paths import agent_dir


def _safe_json_load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _safe_read_list(raw: dict, key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        val = item.strip()
        if not val:
            continue
        if val not in out:
            out.append(val)
    return out


def _agent_skills_config_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "skills.json"


def ensure_agent_skills_config(agent_id: int) -> Path:
    p = _agent_skills_config_path(agent_id)
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


def load_agent_skills_config(agent_id: int) -> dict:
    ensure_agent_skills_config(agent_id)
    raw = _safe_json_load(_agent_skills_config_path(agent_id))
    return {
        "enable_agent_local_skills": bool(raw.get("enable_agent_local_skills", True)),
        "pool_skill_codes": _safe_read_list(raw, "pool_skill_codes"),
    }


def save_agent_skills_config(agent_id: int, *, enable_agent_local_skills: bool, pool_skill_codes: list[str]) -> dict:
    ensure_agent_skills_config(agent_id)
    out = {
        "enable_agent_local_skills": bool(enable_agent_local_skills),
        "pool_skill_codes": _safe_read_list({"pool_skill_codes": pool_skill_codes}, "pool_skill_codes"),
    }
    _agent_skills_config_path(agent_id).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _pool_root() -> Path:
    p = Path(settings.skill_pool_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_skill_pool() -> list[dict]:
    root = _pool_root()
    out: list[dict] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists() or not skill_md.is_file():
            continue
        name = child.name
        description = ""
        try:
            parsed = frontmatter.loads(skill_md.read_text(encoding="utf-8"))
            name = str(parsed.get("name") or name)
            description = str(parsed.get("description") or "")
        except Exception:
            pass
        out.append(
            {
                "code": child.name,
                "name": name,
                "description": description,
                "dir": child.as_posix(),
            }
        )
    return out


def get_skill_loader_specs_for_agent(agent_id: int) -> list[tuple[str, bool]]:
    cfg = load_agent_skills_config(agent_id)
    dirs: list[tuple[str, bool]] = []

    # 1) Global pool: choose by skill code
    pool_root = _pool_root()
    for code in cfg.get("pool_skill_codes", []):
        skill_dir = (pool_root / code).resolve()
        if not skill_dir.exists() or not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        dirs.append((skill_dir.as_posix(), False))

    # 2) Agent-local skills folder (recursive)
    if bool(cfg.get("enable_agent_local_skills", True)):
        local_dir = (agent_dir(agent_id) / "skills").resolve()
        local_dir.mkdir(parents=True, exist_ok=True)
        dirs.append((local_dir.as_posix(), True))

    # de-dup
    unique: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for d, scan_subdir in dirs:
        if d in seen:
            continue
        seen.add(d)
        unique.append((d, scan_subdir))
    return unique
