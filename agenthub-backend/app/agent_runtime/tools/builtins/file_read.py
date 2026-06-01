from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.services.storage_paths import agent_dir
from app.agent_runtime.tools.builtins.common import mark_read, safe_resolve_under_agent


def spec() -> dict:
    return {
        "name": "File Read",
        "code": "file_read",
        "description": "Read text file under agent workspace allowed roots.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    rel_path = str(args.get("path") or "")
    p = safe_resolve_under_agent(agent_id, rel_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    rel = p.relative_to(agent_dir(agent_id)).as_posix()
    mark_read(runtime_context, rel)
    return {"path": rel, "content": p.read_text(encoding="utf-8"), "trace": trace}

