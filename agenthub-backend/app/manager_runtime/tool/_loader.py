from __future__ import annotations

from sqlalchemy.orm import Session

from app.manager_runtime.tool._registry import get_manager_tool_factories


def load_manager_tools(db: Session) -> dict[str, object]:
    tools: dict[str, object] = {}
    for code, factory in get_manager_tool_factories().items():
        tools[code] = factory(db)
    return tools
