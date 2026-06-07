from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import ManagerRuntimeContextMixin, build_error_chunk, build_tool_chunk
from app.services.group_task_service import patch_dag


class DagPatchTool(ManagerRuntimeContextMixin, ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.set_runtime_context(None)
        self.name = "manager.dag_patch"
        self.description = "Create, update, and delete DAG nodes and edges for a task run. If run_id is omitted, use the current conversation task context."
        self.input_schema = {
            "type": "object",
            "properties": {
                "run_id": {"type": "integer"},
                "ops": {"type": "array"},
            },
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        run_id = self._resolve_run_id(kwargs.get("run_id"))
        ops = list(kwargs.get("ops") or [])
        if run_id is None:
            return build_tool_chunk(
                {
                    "ok": False,
                    "error": "run_id_required_for_patch",
                    "available_runs": self._list_group_runs(),
                }
            )
        if not ops:
            return build_error_chunk("ops_required")
        result = patch_dag(
            self._db,
            run_id=int(run_id),
            ops=ops,
        )
        return build_tool_chunk(
            {
                "group_id": int(result.group_id),
                "run_id": int(result.run_id),
                "node_count": int(result.node_count),
                "edge_count": int(result.edge_count),
                "created_node_keys": list(result.created_node_keys),
                "updated_node_keys": list(result.updated_node_keys),
                "deleted_node_keys": list(result.deleted_node_keys),
                "summary": {
                    "created": len(result.created_node_keys),
                    "updated": len(result.updated_node_keys),
                    "deleted": len(result.deleted_node_keys),
                },
            }
        )
