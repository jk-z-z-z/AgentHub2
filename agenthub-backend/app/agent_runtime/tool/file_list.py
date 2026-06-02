from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.common.file_utils import normalize_rel_path
from app.services.storage_paths import agent_dir
from .common import safe_resolve_under_agent


def spec() -> dict:
    return {
        "name": "File List",
        "code": "file_list",
        "description": "List files/dirs under agent workspace allowed roots.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"dir": {"type": "string"}}, "required": []},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    rel_dir = str(args.get("dir") or "knowledge")
    p = safe_resolve_under_agent(agent_id, rel_dir)
    if not p.exists():
        return {"entries": [], "trace": trace}
    if not p.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dir is not a directory")
    entries = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        entries.append(
            {
                "name": child.name,
                "path": child.relative_to(agent_dir(agent_id)).as_posix(),
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else 0,
            }
        )
    return {"entries": entries, "trace": trace}

