from __future__ import annotations

from fastapi import HTTPException, status

from app.agent_runtime.tools.builtins import BUILTIN_TOOL_DEFS
from app.agent_runtime.tools.builtins.common import runtime_int
from app.services.storage_init_service import ensure_agent_space


def execute_builtin_tool(*, agent_id: int, tool_code: str, args: dict, runtime_context: dict | None = None) -> dict:
    """
    Builtin tool entrypoint.

    Each tool is implemented as a standalone function under app/agent_runtime/tools/builtins/*.
    """
    ensure_agent_space(agent_id)

    tool = BUILTIN_TOOL_DEFS.get(str(tool_code))
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # Traceability (optional): associate tool results to group-task run/node.
    run_id = runtime_int(runtime_context, "run_id")
    node_id = runtime_int(runtime_context, "node_id")
    trace = {"run_id": run_id, "node_id": node_id} if (run_id or node_id) else None

    return tool.handler(int(agent_id), args or {}, runtime_context, trace)

