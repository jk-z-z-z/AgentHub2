from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.group_task_service import get_dag_view


class DagViewTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.dag_view"
        self.description = "Inspect the DAG view for a group."
        self.input_schema = {
            "type": "object",
            "properties": {"group_id": {"type": "integer"}},
            "required": ["group_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        group_id = kwargs.get("group_id")
        if group_id in (None, ""):
            return build_error_chunk("group_id_required")
        return build_tool_chunk(get_dag_view(self._db, group_id=int(group_id)))
