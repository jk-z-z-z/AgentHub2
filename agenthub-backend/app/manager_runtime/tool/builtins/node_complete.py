from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.group_task.node_status_service import complete_node


class NodeCompleteTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.node_complete"
        self.description = "Mark a node as completed."
        self.input_schema = {
            "type": "object",
            "properties": {
                "node_id": {"type": "integer"},
                "member_id": {"type": "integer"},
                "output_summary": {"type": "string"},
            },
            "required": ["node_id", "member_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        node_id = kwargs.get("node_id")
        member_id = kwargs.get("member_id")
        output_summary = str(kwargs.get("output_summary") or "").strip()
        if node_id in (None, "") or member_id in (None, ""):
            return build_error_chunk("node_id_and_member_id_required")
        row = complete_node(self._db, node_id=int(node_id), member_id=int(member_id), output_summary=output_summary)
        return build_tool_chunk(
            {
                "node_id": int(row.id),
                "node_key": row.node_key,
                "status": row.status,
                "output_summary": row.output_summary,
            }
        )
