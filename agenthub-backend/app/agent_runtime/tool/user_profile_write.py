from __future__ import annotations

import json

from app.common.file_utils import write_text
from .common import require_user, user_profile_path


def spec() -> dict:
    return {
        "name": "User Profile Write",
        "code": "user_profile_write",
        "description": "Update current user's PROFILE.md in personal context.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"content": {"type": "string"}, "mode": {"type": "string"}}, "required": ["content"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    user_id = require_user(runtime_context)
    content = str(args.get("content") or "")
    mode = str(args.get("mode") or "overwrite")
    path = user_profile_path(user_id)
    write_text(path, content, mode)
    return {"path": path.as_posix(), "written": True, "mode": mode, "trace": trace}

