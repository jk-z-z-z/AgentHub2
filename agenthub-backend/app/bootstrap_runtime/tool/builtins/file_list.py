from __future__ import annotations

import json

from agentscope.tool import ToolBase, ToolChunk

from app.bootstrap_runtime.tool.base import build_error_chunk, build_tool_chunk, permission_passthrough_decision
from app.bootstrap_runtime.tool.common import agent_root, safe_resolve_under_agent


class FileListTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self) -> None:
        self.name = "bootstrap.file_list"
        self.description = "List files under the agent bootstrap workspace."
        self.input_schema = {
            "type": "object",
            "properties": {"agent_id": {"type": "integer"}, "dir": {"type": "string"}},
            "required": ["agent_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return permission_passthrough_decision()

    async def __call__(self, **kwargs) -> ToolChunk:
        agent_id = kwargs.get("agent_id")
        if agent_id in (None, ""):
            return build_error_chunk("agent_id_required")
        rel_dir = str(kwargs.get("dir") or "").strip()
        root = agent_root(int(agent_id))
        target = root if not rel_dir else safe_resolve_under_agent(int(agent_id), rel_dir)
        if not target.exists():
            return build_tool_chunk({"entries": []})
        if not target.is_dir():
            return build_error_chunk("dir is not a directory")
        entries = []
        for child in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            entries.append(
                {
                    "name": child.name,
                    "path": child.relative_to(root).as_posix(),
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else 0,
                }
            )
        return build_tool_chunk({"entries": entries})
