from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.group_task.dag_service import patch_dag


class DagPatchTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.dag_patch"
        self.description = "Create, update, and delete DAG nodes and edges."
        self.input_schema = {
            "type": "object",
            "properties": {
                "group_id": {"type": "integer"},
                "ops": {"type": "array"},
            },
            "required": ["group_id", "ops"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        group_id = kwargs.get("group_id")
        ops = list(kwargs.get("ops") or [])
        if group_id in (None, ""):
            return build_error_chunk("group_id_required")
        if not ops:
            return build_error_chunk("ops_required")
        result = patch_dag(
            self._db,
            group_id=int(group_id),
            ops=ops,
        )
        return build_tool_chunk(
            {
                "group_id": int(result.group_id),
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
