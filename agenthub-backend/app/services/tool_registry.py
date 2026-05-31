from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.models.tool import Tool


def builtin_tools() -> list[dict]:
    """
    Tool definitions are owned by the project (not user-generated).
    This registry seeds metadata into DB for UI listing & agent enable toggles.
    """
    return [
        {
            "name": "File List",
            "code": "file_list",
            "description": "List files/dirs under agent workspace allowed roots.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {"dir": {"type": "string", "description": "e.g. knowledge, skills, mcps"}},
                    "required": [],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "File Read",
            "code": "file_read",
            "description": "Read text file under agent workspace allowed roots.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "e.g. knowledge/notes.md or skills/xxx.md"}},
                    "required": ["path"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "File Write",
            "code": "file_write",
            "description": "Write text file under agent workspace allowed roots.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "e.g. knowledge/notes.md or mcps/config.json"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Project Code List",
            "code": "project_code_list",
            "description": "List files and folders under current project group's shared/code.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {"dir": {"type": "string", "description": "optional subdirectory under project shared/code"}},
                    "required": [],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Project Code Read",
            "code": "project_code_read",
            "description": "Read a text file under current project group's shared/code.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "path under project shared/code"}},
                    "required": ["path"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Worker File List",
            "code": "worker_file_list",
            "description": "List files in runtime workspace or project shared/code for coding work.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["runtime_workspace", "project_code"]},
                        "dir": {"type": "string", "description": "optional subdirectory"},
                    },
                    "required": ["scope"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Worker File Read",
            "code": "worker_file_read",
            "description": "Read files in runtime workspace or project shared/code for coding work.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["runtime_workspace", "project_code"]},
                        "path": {"type": "string"},
                    },
                    "required": ["scope", "path"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "User Profile Write",
            "code": "user_profile_write",
            "description": "Update current user's PROFILE.md in personal context.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "mode": {"type": "string", "enum": ["overwrite", "append"]},
                    },
                    "required": ["content"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Agent Spec Write",
            "code": "agent_spec_write",
            "description": "Write agent core spec markdown files (SOUL/AGENTS/PROFILE/BOOTSTRAP/MEMORY/HEARTBEAT).",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "enum": ["SOUL.md", "AGENTS.md", "PROFILE.md", "BOOTSTRAP.md", "MEMORY.md", "HEARTBEAT.md"],
                        },
                        "content": {"type": "string"},
                        "mode": {"type": "string", "enum": ["overwrite", "append"]},
                    },
                    "required": ["filename", "content"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Worker File Write",
            "code": "worker_file_write",
            "description": "Write files for work output (runtime workspace or project shared/code in project chats).",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["runtime_workspace", "project_code"]},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "mode": {"type": "string", "enum": ["overwrite", "append"]},
                    },
                    "required": ["scope", "path", "content"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Project Command Run",
            "code": "project_command_run",
            "description": "Run a restricted validation command in current project code directory.",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": ["npm run type-check", "npm run build", "pnpm run type-check", "pnpm run build", "yarn type-check", "yarn build"],
                        }
                    },
                    "required": ["command"],
                },
                ensure_ascii=False,
            ),
            "is_active": 1,
        },
        {
            "name": "Web Search",
            "code": "web_search",
            "description": "Search the web (placeholder).",
            "source_type": "builtin",
            "schema_json": json.dumps(
                {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                ensure_ascii=False,
            ),
            "is_active": 0,
        },
    ]


def ensure_builtin_tools_seeded() -> None:
    db = SessionLocal()
    try:
        for spec in builtin_tools():
            code = spec["code"]
            exists = db.query(Tool).filter(Tool.code == code).first()
            if exists:
                # keep name/description/schema up to date
                exists.name = spec["name"]
                exists.description = spec.get("description")
                exists.source_type = spec["source_type"]
                exists.schema_json = spec.get("schema_json") or "{}"
                exists.is_active = int(spec.get("is_active", 1))
                db.add(exists)
            else:
                db.add(Tool(**spec))
        db.commit()
    finally:
        db.close()
