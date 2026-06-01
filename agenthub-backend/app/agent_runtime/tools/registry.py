from __future__ import annotations

from app.db.session import SessionLocal
from app.models.tool import Tool
from app.agent_runtime.tools.builtins import BUILTIN_TOOL_DEFS


def builtin_tools() -> list[dict]:
    # Seed specs only (no handlers).
    return [v.spec for _, v in sorted(BUILTIN_TOOL_DEFS.items(), key=lambda kv: kv[0])]


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

