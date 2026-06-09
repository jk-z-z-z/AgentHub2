from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.mcp import MCP
from app.services.storage_paths import agent_dir


def _mcps_json_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "mcps.json"


def _write_mcps_json(agent_id: int, enabled: dict[str, bool]) -> None:
    p = _mcps_json_path(agent_id)
    enabled_codes = [code for code, is_enabled in (enabled or {}).items() if bool(is_enabled)]
    p.write_text(
        json.dumps({"enabled_codes": sorted(enabled_codes)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_mcps_json(agent_id: int) -> set[str]:
    p = _mcps_json_path(agent_id)
    if not p.exists():
        return set()
    try:
        raw = json.loads(p.read_text(encoding="utf-8") or "{}")
        if isinstance(raw, dict) and isinstance(raw.get("enabled_codes"), list):
            return {str(code) for code in raw.get("enabled_codes", []) if isinstance(code, str) and str(code).strip()}
    except Exception:
        return set()
    return set()


def _list_active_mcp_codes(db: Session) -> list[str]:
    rows = (
        db.query(MCP.server_code)
        .filter(MCP.is_active == 1)
        .order_by(MCP.id.asc())
        .all()
    )
    return [str(row[0]) for row in rows]


def _normalize_toggles(enabled: set[str], allowed_codes: list[str]) -> dict[str, bool]:
    normalized = {str(code): False for code in allowed_codes}
    for code in enabled:
        if code in normalized:
            normalized[code] = True
    return normalized


def get_agent_mcp_toggles(db: Session, *, agent_id: int, creator_user_id: int) -> dict[str, bool]:
    agent = db.query(AgentInstance).filter(AgentInstance.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if int(agent.creator_user_id) != int(creator_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    stored = _read_mcps_json(int(agent_id))
    allowed_codes = _list_active_mcp_codes(db)
    normalized = _normalize_toggles(stored, allowed_codes)
    _write_mcps_json(int(agent_id), normalized)
    return normalized


def update_agent_mcp_toggles(
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

    allowed_codes = _list_active_mcp_codes(db)
    normalized = _normalize_toggles({str(k) for k, v in (enabled or {}).items() if bool(v)}, allowed_codes)
    _write_mcps_json(int(agent_id), normalized)
    return normalized
