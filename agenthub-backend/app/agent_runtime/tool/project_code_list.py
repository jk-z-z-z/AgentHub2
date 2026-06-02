from __future__ import annotations

import json

from app.common.file_utils import list_dir_entries, safe_resolve_under_root
from .common import project_code_root, require_project_group


def spec() -> dict:
    return {
        "name": "Project Code List",
        "code": "project_code_list",
        "description": "List files and folders under current project group's shared/code.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"dir": {"type": "string"}}, "required": []},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    group_id = require_project_group(runtime_context)
    root = project_code_root(group_id)
    rel_dir = str(args.get("dir") or "").strip()
    target = root if not rel_dir else safe_resolve_under_root(root, rel_dir)
    if not target.exists():
        return {"entries": [], "trace": trace}
    if not target.is_dir():
        return {"entries": [], "trace": trace}
    return {"entries": list_dir_entries(root, target), "trace": trace}

