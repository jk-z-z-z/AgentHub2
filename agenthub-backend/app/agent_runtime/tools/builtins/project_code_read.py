from __future__ import annotations

import json

from app.common.file_utils import normalize_rel_path
from app.services.project_code_service import read_project_code_file
from app.agent_runtime.tools.builtins.common import require_project_group


def spec() -> dict:
    return {
        "name": "Project Code Read",
        "code": "project_code_read",
        "description": "Read a text file under current project group's shared/code.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    group_id = require_project_group(runtime_context)
    rel_path = str(args.get("path") or "")
    content = read_project_code_file(group_id, rel_path)
    return {"path": normalize_rel_path(rel_path), "content": content, "trace": trace}

