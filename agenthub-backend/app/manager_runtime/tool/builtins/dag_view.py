from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import ManagerRuntimeContextMixin, build_tool_chunk
from app.services.group_task_service import get_dag_view


class DagViewTool(ManagerRuntimeContextMixin, ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.set_runtime_context(None)
        self.name = "manager.dag_view"
        self.description = "Inspect the DAG view for a task run. If run_id is omitted, try the current conversation task context."
        self.input_schema = {
            "type": "object",
            "properties": {"run_id": {"type": "integer"}},
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        run_id = self._resolve_run_id(kwargs.get("run_id"))
        if run_id is None:
            return build_tool_chunk(
                {
                    "resolved_run_id": None,
                    "nodes": [],
                    "edges": [],
                    "available_runs": self._list_group_runs(),
                    "hint": "No current run is bound to this conversation. Create a new run or pass run_id explicitly.",
                }
            )
        payload = get_dag_view(self._db, run_id=int(run_id))
        payload["resolved_run_id"] = int(run_id)
        payload["available_runs"] = self._list_group_runs()
        return build_tool_chunk(payload)
