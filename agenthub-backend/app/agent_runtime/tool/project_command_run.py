from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.services.execution_runtime_service import create_and_run_execution_job
from app.services.workspace_runtime_service import ensure_workspace_for_project_id
from .common import require_project_group, runtime_int



def spec() -> dict:
    return {
        "name": "Project Command Run",
        "code": "project_command_run",
        "description": "Run a sandboxed command against the current project workspace.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "sandbox_image": {"type": "string"},
                    "network_enabled": {"type": "boolean"},
                    "env": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["command"],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    group_id = require_project_group(runtime_context)
    command = str(args.get("command") or "").strip()
    cwd = str(args.get("cwd") or ".")
    sandbox_image = str(args.get("sandbox_image") or "").strip() or None
    network_enabled = bool(args.get("network_enabled") or False)
    env = args.get("env") if isinstance(args.get("env"), dict) else {}

    db = SessionLocal()
    try:
        workspace = ensure_workspace_for_project_id(db, project_id=int(group_id))
        effective_user_id = runtime_int(runtime_context, "user_id") or int(workspace.creator_user_id)
    finally:
        db.close()

    result = create_and_run_execution_job(
        workspace_id=int(workspace.id),
        user_id=int(effective_user_id),
        command=command,
        cwd=cwd,
        sandbox_image=sandbox_image,
        network_enabled=network_enabled,
        env={str(k): str(v) for k, v in env.items()},
    )
    payload = {
        "execution_job_id": int(result["id"]),
        "workspace_id": int(result["workspace_id"]),
        "command": command,
        "cwd": cwd,
        "exit_code": int((result.get("result") or {}).get("exit_code", 1)),
        "stdout": str(result.get("stdout") or ""),
        "stderr": str(result.get("stderr") or ""),
        "ok": str(result.get("status") or "") == "succeeded",
        "trace": trace,
    }
    return payload
