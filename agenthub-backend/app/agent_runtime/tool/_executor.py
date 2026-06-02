from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from ._builtins_init import BUILTIN_TOOL_DEFS
from .common import runtime_int
from app.services.storage_init_service import ensure_agent_space


def execute_builtin_tool(
    *,
    agent_id: int,
    tool_code: str,
    args: dict[str, Any],
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_agent_space(agent_id)

    tool = BUILTIN_TOOL_DEFS.get(str(tool_code))
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    run_id = runtime_int(runtime_context, "run_id")
    node_id = runtime_int(runtime_context, "node_id")
    trace = {"run_id": run_id, "node_id": node_id} if (run_id or node_id) else None

    return tool.handler(int(agent_id), args or {}, runtime_context, trace)
