from __future__ import annotations

from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import ToolCallResult
from app.manager_runtime.tool._loader import load_manager_tools


async def execute_manager_tool(
    db: Session,
    *,
    tool_code: str,
    args: dict | None = None,
    group_id: int | None = None,
) -> ToolCallResult:
    tools = load_manager_tools(db)
    tool = tools.get(str(tool_code))
    if not tool:
        return ToolCallResult(ok=False, result={}, error="tool_not_allowed")
    try:
        call_args = dict(args or {})
        if group_id is not None and "group_id" not in call_args:
            call_args["group_id"] = int(group_id)
        return await tool(**call_args)
    except Exception as e:
        return ToolCallResult(ok=False, result={}, error=str(e))
