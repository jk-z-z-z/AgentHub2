from __future__ import annotations

import json
from typing import Any

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk


def build_tool_chunk(payload: Any, *, ok: bool = True) -> ToolChunk:
    return ToolChunk(
        content=[TextBlock(text=json.dumps(payload, ensure_ascii=False, default=str))],
        state=ToolResultState.SUCCESS if ok else ToolResultState.ERROR,
    )


def build_error_chunk(error: str) -> ToolChunk:
    return build_tool_chunk({"error": error}, ok=False)
