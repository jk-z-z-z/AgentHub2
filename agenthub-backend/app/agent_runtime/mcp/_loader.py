from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.mcp import MCP
from app.services.storage_paths import agent_dir


def _get_mcp_config_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "mcps.json"


def load_enabled_mcps_for_agent(db: Session, agent_id: int) -> list[dict[str, Any]]:
    mcp_config_path = _get_mcp_config_path(int(agent_id))
    enabled_codes: set[str] = set()
    if mcp_config_path.exists():
        try:
            raw = json.loads(mcp_config_path.read_text(encoding="utf-8") or "{}")
            if isinstance(raw, dict) and isinstance(raw.get("enabled_codes"), list):
                for code in raw.get("enabled_codes", []):
                    if isinstance(code, str):
                        enabled_codes.add(code)
        except Exception:
            pass

    if not enabled_codes:
        return []

    rows = (
        db.query(MCP)
        .filter(MCP.is_active == 1)
        .order_by(MCP.id.asc())
        .all()
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        if str(getattr(row, "server_code", "")) in enabled_codes:
            results.append({
                "id": int(getattr(row, "id", 0)),
                "name": str(getattr(row, "name", "")),
                "server_code": str(getattr(row, "server_code", "")),
                "connection_json": json.loads(str(getattr(row, "connection_json", "{}"))),
            })
    return results
