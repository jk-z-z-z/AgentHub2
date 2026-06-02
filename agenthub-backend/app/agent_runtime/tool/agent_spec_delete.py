from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.services.storage_paths import agent_dir


ALLOWED_DELETE_FILES: set[str] = {"BOOTSTRAP.md"}


def spec() -> dict:
    return {
        "name": "Agent Spec Delete",
        "code": "agent_spec_delete",
        "description": "Delete a temporary agent spec file (bootstrap lifecycle).",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    filename = str(args.get("filename") or "")
    if filename not in ALLOWED_DELETE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"filename must be one of: {', '.join(sorted(ALLOWED_DELETE_FILES))}",
        )
    path = agent_dir(agent_id) / filename
    if path.exists() and path.is_file():
        path.unlink()
    return {"filename": filename, "deleted": True, "trace": trace}

