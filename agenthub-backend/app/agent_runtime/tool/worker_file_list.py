from __future__ import annotations

import json

from app.common.file_utils import list_dir_entries, safe_resolve_under_root
from .common import resolve_worker_root


def spec() -> dict:
    return {
        "name": "Worker File List",
        "code": "worker_file_list",
        "description": "List files in runtime workspace or project shared/code for coding work.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"scope": {"type": "string"}, "dir": {"type": "string"}}, "required": ["scope"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    scope = str(args.get("scope") or "")
    rel_dir = str(args.get("dir") or "").strip()
    root = resolve_worker_root(agent_id, scope, runtime_context)
    root.mkdir(parents=True, exist_ok=True)
    target = root if not rel_dir else safe_resolve_under_root(root, rel_dir)
    if not target.exists():
        return {"entries": [], "trace": trace}
    if not target.is_dir():
        return {"entries": [], "trace": trace}
    return {"entries": list_dir_entries(root, target), "trace": trace}
