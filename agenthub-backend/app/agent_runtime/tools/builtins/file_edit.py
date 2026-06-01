from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.services.storage_paths import agent_dir
from app.agent_runtime.tools.builtins.common import mark_read, safe_resolve_under_agent


def spec() -> dict:
    return {
        "name": "File Edit",
        "code": "file_edit",
        "description": "Edit a text file by replacing an exact substring (safe, deterministic).",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "expected_replacements": {"type": "integer", "description": "If provided, enforce exact replacement count."},
                },
                "required": ["path", "old_text", "new_text"],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    rel_path = str(args.get("path") or "")
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    expected = args.get("expected_replacements", None)

    p = safe_resolve_under_agent(agent_id, rel_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    rel = p.relative_to(agent_dir(agent_id)).as_posix()
    mark_read(runtime_context, rel)

    text = p.read_text(encoding="utf-8")
    count = text.count(old_text)
    if count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="old_text not found")
    if expected is not None:
        try:
            expected_n = int(expected)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_replacements must be an integer")
        if count != expected_n:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"replacement count mismatch: found={count} expected={expected_n}",
            )
    updated = text.replace(old_text, new_text)
    p.write_text(updated, encoding="utf-8")
    mark_read(runtime_context, rel)
    return {"path": rel, "edited": True, "replacements": count, "trace": trace}

