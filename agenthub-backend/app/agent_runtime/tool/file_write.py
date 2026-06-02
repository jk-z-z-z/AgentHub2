from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.services.storage_paths import agent_dir
from .common import mark_read, safe_resolve_under_agent, was_read


def spec() -> dict:
    return {
        "name": "File Write",
        "code": "file_write",
        "description": "Write text file under agent workspace allowed roots.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "force": {"type": "boolean", "description": "Allow overwrite without prior file_read (not recommended)."},
                },
                "required": ["path", "content"],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    rel_path = str(args.get("path") or "")
    content = str(args.get("content") or "")
    force = bool(args.get("force") or False)
    p = safe_resolve_under_agent(agent_id, rel_path)
    rel = p.relative_to(agent_dir(agent_id)).as_posix()
    if p.exists() and p.is_file() and not force and not was_read(runtime_context, rel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_write requires prior file_read for existing files (or pass force=true)",
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    mark_read(runtime_context, rel)
    return {"path": rel, "written": True, "trace": trace}

