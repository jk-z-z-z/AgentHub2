from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk

from app.bootstrap_runtime.tool.base import build_error_chunk, build_tool_chunk, permission_passthrough_decision
from app.bootstrap_runtime.tool.common import agent_root, safe_resolve_under_agent
from app.common.file_utils import write_text


class FileWriteTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self) -> None:
        self.name = "bootstrap.file_write"
        self.description = "Write files under the agent bootstrap workspace."
        self.input_schema = {
            "type": "object",
            "properties": {
                "agent_id": {"type": "integer"},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string"},
            },
            "required": ["agent_id", "path", "content"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return permission_passthrough_decision()

    async def __call__(self, **kwargs) -> ToolChunk:
        agent_id = kwargs.get("agent_id")
        path = str(kwargs.get("path") or "").strip()
        content = str(kwargs.get("content") or "")
        mode = str(kwargs.get("mode") or "overwrite")
        if agent_id in (None, ""):
            return build_error_chunk("agent_id_required")
        if not path:
            return build_error_chunk("path_required")
        target = safe_resolve_under_agent(int(agent_id), path)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, content, mode)
        return build_tool_chunk({"path": target.relative_to(agent_root(int(agent_id))).as_posix(), "written": True, "mode": mode})
