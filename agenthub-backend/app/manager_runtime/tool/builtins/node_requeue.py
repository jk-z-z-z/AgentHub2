from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.group_task_service import requeue_node


class NodeRequeueTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.node_requeue"
        self.description = "Requeue a node for another pass after manager review."
        self.input_schema = {
            "type": "object",
            "properties": {
                "node_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["node_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        node_id = kwargs.get("node_id")
        if node_id in (None, ""):
            return build_error_chunk("node_id_required")
        row = requeue_node(self._db, node_id=int(node_id), reason=str(kwargs.get("reason") or "").strip())
        return build_tool_chunk(
            {
                "node_id": int(row.id),
                "node_key": row.node_key,
                "status": row.status,
                "attempt": int(row.attempt or 0),
                "error": row.error,
            }
        )
