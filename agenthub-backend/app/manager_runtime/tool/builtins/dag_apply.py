from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.group_task_service import list_nodes, replace_run_nodes, resolve_run


class DagApplyTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.dag_apply"
        self.description = "Replace the DAG for a task run with a structured graph."
        self.input_schema = {
            "type": "object",
            "properties": {
                "run_id": {"type": "integer"},
                "graph": {"type": "object"},
            },
            "required": ["run_id", "graph"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        run_id = kwargs.get("run_id")
        graph = dict(kwargs.get("graph") or {})
        if run_id in (None, ""):
            return build_error_chunk("run_id_required")
        nodes = list(graph.get("nodes") or [])
        run = resolve_run(self._db, run_id=int(run_id))
        current = list_nodes(self._db, run_id=int(run_id))
        action = "updated" if current else "created"
        replace_run_nodes(self._db, run_id=int(run_id), nodes=nodes)
        return build_tool_chunk(
            {
                "action": action,
                "group_id": int(run.group_id),
                "run_id": int(run.id),
                "node_count": len(nodes),
            }
        )
