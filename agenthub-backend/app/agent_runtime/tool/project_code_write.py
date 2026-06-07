from __future__ import annotations

import json

from app.services.project_code_service import write_project_code_file
from .common import require_project_group


def spec() -> dict:
    return {
        "name": "Project Code Write",
        "code": "project_code_write",
        "description": "Write a UTF-8 text file under project shared/code.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    _ = agent_id
    group_id = require_project_group(runtime_context)
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    payload = write_project_code_file(group_id, path, content)
    return {
        "path": str(payload["path"]),
        "content": str(payload["content"]),
        "trace": trace,
    }
