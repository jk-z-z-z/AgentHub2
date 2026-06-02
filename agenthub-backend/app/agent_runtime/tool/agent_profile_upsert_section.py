from __future__ import annotations

import json

from fastapi import HTTPException, status

from .common import agent_profile_path


def spec() -> dict:
    return {
        "name": "Agent Profile Upsert Section",
        "code": "agent_profile_upsert_section",
        "description": "Upsert a named section inside agent PROFILE.md using stable markers (idempotent).",
        "source_type": "builtin",
        "schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "section_key": {"type": "string", "description": "Stable key, e.g. api_contract / conventions / decisions"},
                    "title": {"type": "string", "description": "Optional heading title shown in PROFILE.md"},
                    "content": {"type": "string", "description": "Markdown content for the section body"},
                },
                "required": ["section_key", "content"],
            },
            ensure_ascii=False,
        ),
        "is_active": 1,
    }


def run(agent_id: int, args: dict, runtime_context: dict | None, trace: dict) -> dict:
    section_key = str(args.get("section_key") or "").strip()
    if not section_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="section_key is required")
    title = str(args.get("title") or "").strip() or section_key
    content = str(args.get("content") or "")
    path = agent_profile_path(agent_id)

    start_marker = f"<!-- AGENTHUB_SECTION:{section_key} -->"
    end_marker = f"<!-- /AGENTHUB_SECTION:{section_key} -->"

    try:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        existing = ""

    block = "\n".join(
        [
            start_marker,
            f"## {title}",
            (content or "").rstrip(),
            end_marker,
            "",
        ]
    )

    if start_marker in existing and end_marker in existing:
        before, rest = existing.split(start_marker, 1)
        _, after = rest.split(end_marker, 1)
        updated = (before.rstrip() + "\n\n" + block + after.lstrip()).rstrip() + "\n"
    else:
        updated = (existing.rstrip() + "\n\n" + block).rstrip() + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return {"filename": "PROFILE.md", "section_key": section_key, "written": True, "trace": trace}

