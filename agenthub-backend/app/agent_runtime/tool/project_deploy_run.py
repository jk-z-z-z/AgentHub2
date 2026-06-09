from __future__ import annotations

import json
import re

from app.db.session import SessionLocal
from app.models.group import Group
from app.services.deployment_runtime_service import create_and_run_deployment_job
from app.services.workspace_runtime_service import ensure_workspace_for_project_id
from .common import require_project_group, runtime_int


def _slugify(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(text or "").strip().lower())
    return normalized.strip("-")[:48] or "project"


def _default_image_ref(*, project_name: str, run_id: int | None) -> str:
    slug = _slugify(project_name)
    if run_id is not None:
        return f"agenthub/{slug}-run-{int(run_id)}:latest"
    return f"agenthub/{slug}:latest"


def _default_container_name(*, project_name: str, run_id: int | None) -> str:
    slug = _slugify(project_name)
    if run_id is not None:
        return f"agenthub-{slug}-run-{int(run_id)}"
    return f"agenthub-{slug}"


def spec() -> dict:
    return {
        "name": "Project Deploy Run",
        "code": "project_deploy_run",
        "description": "Run the deployment pipeline for the current project workspace.",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "image_ref": {"type": "string"},
                    "container_name": {"type": "string"},
                    "sandbox_image": {"type": "string"},
                    "dockerfile_path": {"type": "string"},
                    "build_context_path": {"type": "string"},
                    "install_command": {"type": "string"},
                    "test_command": {"type": "string"},
                    "build_command": {"type": "string"},
                    "container_command": {"type": "string"},
                    "env": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "ports": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "host_port": {"type": "integer"},
                                "container_port": {"type": "integer"},
                                "protocol": {"type": "string"},
                            },
                            "required": ["container_port"],
                        },
                    },
                },
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    _ = agent_id
    group_id = require_project_group(runtime_context)
    run_id = runtime_int(runtime_context, "run_id")
    node_id = runtime_int(runtime_context, "node_id")
    db = SessionLocal()
    try:
        workspace = ensure_workspace_for_project_id(db, project_id=int(group_id))
        effective_user_id = runtime_int(runtime_context, "user_id") or int(workspace.creator_user_id)
        group = db.query(Group).filter(Group.id == int(group_id)).first()
        project_name = str(group.name or f"project-{int(group_id)}") if group else f"project-{int(group_id)}"
    finally:
        db.close()

    image_ref = str(args.get("image_ref") or "").strip() or _default_image_ref(project_name=project_name, run_id=run_id)
    container_name = str(args.get("container_name") or "").strip() or _default_container_name(project_name=project_name, run_id=run_id)
    if not image_ref or not container_name:
        raise ValueError("image_ref_and_container_name_required")

    result = create_and_run_deployment_job(
        workspace_id=int(workspace.id),
        user_id=int(effective_user_id),
        image_ref=image_ref,
        container_name=container_name,
        sandbox_image=str(args.get("sandbox_image") or "").strip() or None,
        dockerfile_path=str(args.get("dockerfile_path") or "Dockerfile"),
        build_context_path=str(args.get("build_context_path") or "."),
        install_command=str(args.get("install_command") or "").strip() or None,
        test_command=str(args.get("test_command") or "").strip() or None,
        build_command=str(args.get("build_command") or "").strip() or None,
        container_command=str(args.get("container_command") or "").strip() or None,
        env={str(k): str(v) for k, v in (args.get("env") or {}).items()} if isinstance(args.get("env"), dict) else {},
        ports=[item for item in (args.get("ports") or []) if isinstance(item, dict)],
        runtime_context={
            "run_id": int(run_id) if run_id is not None else None,
            "node_id": int(node_id) if node_id is not None else None,
        },
    )
    resolved_url = None
    spec_payload = result.get("spec") or {}
    if isinstance(spec_payload, dict):
        ports = spec_payload.get("ports")
        if isinstance(ports, list) and ports and isinstance(ports[0], dict):
            try:
                host_port = int(ports[0].get("host_port"))
            except (TypeError, ValueError):
                host_port = None
            if host_port:
                resolved_url = f"http://127.0.0.1:{host_port}"
    return {
        "deployment_job_id": int(result["id"]),
        "workspace_id": int(result["workspace_id"]),
        "status": str(result["status"]),
        "image_ref": str(result["image_ref"]),
        "container_name": str(result["container_name"]),
        "deployed_container_id": result.get("deployed_container_id"),
        "rollback_status": result.get("rollback_status"),
        "error_message": result.get("error_message"),
        "logs_text": str(result.get("logs_text") or ""),
        "url": resolved_url,
        "trace": trace,
    }
