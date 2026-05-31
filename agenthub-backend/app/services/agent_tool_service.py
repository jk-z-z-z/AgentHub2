from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.tool import Tool
from app.services.storage_paths import agent_dir


def _tools_json_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "tools.json"


def _write_tools_json(agent_id: int, enabled: dict[str, bool]) -> None:
    tools_json_path = _tools_json_path(agent_id)
    tools_json_path.write_text(
        json.dumps({"enabled": enabled or {}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_tools_json(agent_id: int) -> dict[str, bool]:
    tools_json_path = _tools_json_path(agent_id)
    if not tools_json_path.exists():
        return {}
    try:
        raw = json.loads(tools_json_path.read_text(encoding="utf-8") or "{}")
        if isinstance(raw, dict) and isinstance(raw.get("enabled"), dict):
            out: dict[str, bool] = {}
            for k, v in raw.get("enabled", {}).items():
                out[str(k)] = bool(v)
            return out
    except Exception:
        return {}
    return {}


def _list_builtin_active_tool_codes(db: Session) -> list[str]:
    rows = (
        db.query(Tool.code)
        .filter(Tool.source_type == "builtin", Tool.is_active == 1)
        .order_by(Tool.id.asc())
        .all()
    )
    return [str(row[0]) for row in rows]


def _normalize_toggles(enabled: dict[str, bool], allowed_codes: list[str]) -> dict[str, bool]:
    allowed = [str(code) for code in allowed_codes]
    merged = {code: True for code in allowed}
    for k, v in (enabled or {}).items():
        key = str(k)
        if key in merged:
            merged[key] = bool(v)
    return merged


def get_agent_tool_toggles(db: Session, *, agent_id: int, creator_user_id: int) -> dict[str, bool]:
    agent = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(agent.creator_user_id) != int(creator_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    stored = _read_tools_json(int(agent_id))
    allowed_codes = _list_builtin_active_tool_codes(db)
    normalized = _normalize_toggles(stored, allowed_codes)
    _write_tools_json(int(agent_id), normalized)
    return normalized


def update_agent_tool_toggles(
    db: Session,
    *,
    agent_id: int,
    creator_user_id: int,
    enabled: dict[str, bool],
) -> dict[str, bool]:
    agent = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(agent.creator_user_id) != int(creator_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    allowed_codes = _list_builtin_active_tool_codes(db)
    normalized = _normalize_toggles(enabled or {}, allowed_codes)
    _write_tools_json(int(agent_id), normalized)
    return normalized


def get_agent_tool_toggles_for_runtime(db: Session, *, agent_id: int) -> dict[str, bool]:
    agent = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not agent:
        return {}
    stored = _read_tools_json(int(agent_id))
    allowed_codes = _list_builtin_active_tool_codes(db)
    normalized = _normalize_toggles(stored, allowed_codes)
    _write_tools_json(int(agent_id), normalized)
    return normalized
