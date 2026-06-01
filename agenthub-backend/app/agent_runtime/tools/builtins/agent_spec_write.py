from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.common.file_utils import write_text
from app.services.storage_paths import agent_dir


ALLOWED_AGENT_SPEC_FILES: set[str] = {"SOUL.md", "PROFILE.md", "BOOTSTRAP.md", "MEMORY.md"}


def spec() -> dict:
    return {
        "name": "Agent Spec Write",
        "code": "agent_spec_write",
        "description": "Write agent core spec markdown files.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}, "mode": {"type": "string"}}, "required": ["filename", "content"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    filename = str(args.get("filename") or "")
    if filename not in ALLOWED_AGENT_SPEC_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"filename must be one of: {', '.join(sorted(ALLOWED_AGENT_SPEC_FILES))}",
        )
    content = str(args.get("content") or "")
    mode = str(args.get("mode") or "overwrite")
    path = agent_dir(agent_id) / filename
    write_text(path, content, mode)
    return {"path": path.relative_to(agent_dir(agent_id)).as_posix(), "written": True, "mode": mode, "trace": trace}

