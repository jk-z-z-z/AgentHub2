from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.services.preview_runtime_service import create_and_run_preview_job
from app.services.workspace_runtime_service import ensure_workspace_for_project_id
from .common import require_project_group, runtime_int


def spec() -> dict:
    return {
        "name": "Project Preview Run",
        "code": "project_preview_run",
        "description": "Create or refresh a persistent local preview for the current project workspace.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "sandbox_image": {"type": "string"},
                    "install_command": {"type": "string"},
                    "build_command": {"type": "string"},
                    "host_port": {"type": "integer"},
                    "env": {"type": "object", "additionalProperties": {"type": "string"}},
                },
                "required": [],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    _ = agent_id
    group_id = require_project_group(runtime_context)
    db = SessionLocal()
    try:
        workspace = ensure_workspace_for_project_id(db, project_id=int(group_id))
        effective_user_id = runtime_int(runtime_context, "user_id") or int(workspace.creator_user_id)
    finally:
        db.close()

    result = create_and_run_preview_job(
        workspace_id=int(workspace.id),
        user_id=int(effective_user_id),
        source_path=str(args.get("source_path") or "."),
        sandbox_image=str(args.get("sandbox_image") or "").strip() or None,
        install_command=str(args.get("install_command") or "").strip() or None,
        build_command=str(args.get("build_command") or "").strip() or None,
        host_port=int(args.get("host_port")) if args.get("host_port") not in (None, "") else None,
        env={str(k): str(v) for k, v in (args.get("env") or {}).items()} if isinstance(args.get("env"), dict) else {},
    )
    return {
        "preview_id": int(result["id"]),
        "workspace_id": int(result["workspace_id"]),
        "status": str(result["status"]),
        "host_port": int(result["host_port"]),
        "url": result.get("url"),
        "container_name": str(result["container_name"]),
        "error_message": result.get("error_message"),
        "trace": trace,
    }
