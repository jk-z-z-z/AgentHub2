from __future__ import annotations

import json
import subprocess

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.project_code_service import get_project_code_root
from app.agent_runtime.tools.builtins.common import require_project_group


ALLOWED_PROJECT_COMMANDS: set[str] = {
    "npm run type-check",
    "npm run build",
    "pnpm run type-check",
    "pnpm run build",
    "yarn type-check",
    "yarn build",
}


def spec() -> dict:
    return {
        "name": "Project Command Run",
        "code": "project_command_run",
        "description": "Run a safe allowlisted command in project shared/code.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    group_id = require_project_group(runtime_context)
    command = str(args.get("command") or "").strip()
    if command not in ALLOWED_PROJECT_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"command must be one of: {', '.join(sorted(ALLOWED_PROJECT_COMMANDS))}",
        )
    root = get_project_code_root(group_id)
    proc = subprocess.run(
        command,
        cwd=root,
        shell=True,
        capture_output=True,
        text=True,
        timeout=max(10, int(settings.project_command_timeout_seconds)),
    )
    return {
        "command": command,
        "cwd": root.as_posix(),
        "exit_code": int(proc.returncode),
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-20000:],
        "ok": proc.returncode == 0,
        "trace": trace,
    }

