from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.models.tool import Tool


def builtin_tools() -> list[dict]:
    return [
        {
            "name": "File List",
            "code": "file_list",
            "description": "List files/dirs under agent workspace allowed roots",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"dir": {"type": "string"}}, "required": []}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "File Read",
            "code": "file_read",
            "description": "Read text file under agent workspace allowed roots",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "File Write",
            "code": "file_write",
            "description": "Write text file under agent workspace allowed roots",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "force": {"type": "boolean"}}, "required": ["path", "content"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "File Edit",
            "code": "file_edit",
            "description": "Edit a file by replacing an exact substring",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}, "expected_replacements": {"type": "integer"}}, "required": ["path", "old_text", "new_text"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Project Code List",
            "code": "project_code_list",
            "description": "List files/folders under project shared/code",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"dir": {"type": "string"}}, "required": []}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Project Code Read",
            "code": "project_code_read",
            "description": "Read a text file under project shared/code",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Worker File List",
            "code": "worker_file_list",
            "description": "List files in runtime workspace or project scope",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"scope": {"type": "string"}, "dir": {"type": "string"}}, "required": ["scope"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Worker File Read",
            "code": "worker_file_read",
            "description": "Read files in runtime workspace or project scope",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"scope": {"type": "string"}, "path": {"type": "string"}}, "required": ["scope", "path"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Worker File Write",
            "code": "worker_file_write",
            "description": "Write files in runtime workspace or project scope",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"scope": {"type": "string"}, "path": {"type": "string"}, "content": {"type": "string"}, "mode": {"type": "string"}}, "required": ["scope", "path", "content"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "User Profile Write",
            "code": "user_profile_write",
            "description": "Update user's PROFILE.md memory file",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"content": {"type": "string"}, "mode": {"type": "string"}}, "required": ["content"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Agent Spec Write",
            "code": "agent_spec_write",
            "description": "Write/update agent specification files in profile dir",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"file": {"type": "string"}, "content": {"type": "string"}}, "required": ["file", "content"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Agent Spec Delete",
            "code": "agent_spec_delete",
            "description": "Delete a file from agent specification profile dir",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"file": {"type": "string"}}, "required": ["file"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Agent Profile Upsert Section",
            "code": "agent_profile_upsert_section",
            "description": "Upsert a named stable-marked section in agent PROFILE.md",
            "source_type": "builtin",
            "schema_json": json.dumps({"type": "object", "properties": {"section_key": {"type": "string", "description": "Stable id for section, e.g. api_contract"}, "title": {"type": "string"}, "content": {"type": "string"}}, "required": ["section_key", "content"]}, ensure_ascii=False),
            "is_active": 1,
        },
        {
            "name": "Project Command Run",
            "code": "project_command_run",
            "description": "Run a sandboxed command under the current project workspace",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                        "sandbox_image": {"type": "string"},
                        "network_enabled": {"type": "boolean"},
                        "env": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                    "required": ["command"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Project Deploy Run",
            "code": "project_deploy_run",
            "description": "Run the deployment pipeline for the current project workspace",
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
                        "env": {"type": "object", "additionalProperties": {"type": "string"}},
                        "ports": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "host_port": {"type": "integer"},
                                    "container_port": {"type": "integer"},
                                    "protocol": {"type": "string"},
                                },
                                "required": ["host_port", "container_port"],
                            },
                        },
                    },
                    "required": ["image_ref", "container_name"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
    ]


def ensure_builtin_tools_seeded() -> None:
    db = SessionLocal()
    try:
        existing = {str(row[0]) for row in db.query(Tool.code).filter(Tool.source_type == "builtin").all()}
        for spec in builtin_tools():
            code = str(spec.get("code") or "")
            if not code:
                continue
            if code in existing:
                continue
            db.add(Tool(**spec))
        db.commit()
    finally:
        db.close()
