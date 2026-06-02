from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.common.file_utils import safe_resolve_under_root
from .common import resolve_worker_root


def spec() -> dict:
    return {
        "name": "Worker File Read",
        "code": "worker_file_read",
        "description": "Read files in runtime workspace or project shared/code for coding work.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"scope": {"type": "string"}, "path": {"type": "string"}}, "required": ["scope", "path"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    scope = str(args.get("scope") or "")
    rel_path = str(args.get("path") or "")
    root = resolve_worker_root(agent_id, scope, runtime_context)
    root.mkdir(parents=True, exist_ok=True)
    target = safe_resolve_under_root(root, rel_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return {"path": target.relative_to(root).as_posix(), "scope": scope, "content": target.read_text(encoding="utf-8"), "trace": trace}

