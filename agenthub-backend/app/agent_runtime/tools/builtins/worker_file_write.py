from __future__ import annotations

import json

from app.common.file_utils import safe_resolve_under_root, write_text
from app.agent_runtime.tools.builtins.common import resolve_worker_root


def spec() -> dict:
    return {
        "name": "Worker File Write",
        "code": "worker_file_write",
        "description": "Write files for work output.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"scope": {"type": "string"}, "path": {"type": "string"}, "content": {"type": "string"}, "mode": {"type": "string"}}, "required": ["scope", "path", "content"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    scope = str(args.get("scope") or "runtime_workspace")
    rel_path = str(args.get("path") or "")
    content = str(args.get("content") or "")
    mode = str(args.get("mode") or "overwrite")
    root = resolve_worker_root(agent_id, scope, runtime_context)
    root.mkdir(parents=True, exist_ok=True)
    target = safe_resolve_under_root(root, rel_path)
    write_text(target, content, mode)
    return {"path": target.relative_to(root).as_posix(), "scope": scope, "written": True, "mode": mode, "trace": trace}

