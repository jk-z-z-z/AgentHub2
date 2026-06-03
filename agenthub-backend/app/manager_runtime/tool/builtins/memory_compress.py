from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.memory_runtime.facade import compress_project_memory, get_project_memory_compressor_status


class ProjectMemoryCompressTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, db: Session) -> None:
        self._db = db
        self.name = "manager.memory_compress"
        self.description = "Compress project conversation memory into PROJECT/MEMORY.md."
        self.input_schema = {
            "type": "object",
            "properties": {
                "group_id": {"type": "integer"},
            },
            "required": ["group_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        group_id = kwargs.get("group_id")
        if group_id in (None, ""):
            return build_error_chunk("group_id_required")
        result = await compress_project_memory(self._db, project_id=int(group_id))
        status = get_project_memory_compressor_status(self._db, project_id=int(group_id))
        return build_tool_chunk(
            {
                "group_id": int(group_id),
                "compressed": bool(result.get("compressed")),
                "reason": result.get("reason"),
                "last_message_id": status.get("last_message_id"),
                "pending_tokens": status.get("pending_tokens"),
            }
        )
