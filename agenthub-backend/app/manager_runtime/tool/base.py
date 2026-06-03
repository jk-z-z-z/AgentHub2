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


def extract_tool_result(chunk: Any) -> dict[str, Any]:
    state = getattr(chunk, "state", None)
    content = getattr(chunk, "content", None) or []
    text_parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            text_parts.append(str(part.get("text") or ""))
            continue
        if getattr(part, "type", None) == "text":
            text_parts.append(str(getattr(part, "text", "") or ""))
            continue
        if hasattr(part, "text"):
            text_parts.append(str(getattr(part, "text", "") or ""))
    raw_text = "".join(text_parts).strip()
    if not raw_text:
        return {"ok": state != ToolResultState.ERROR, "result": {}, "error": None}
    try:
        payload = json.loads(raw_text)
    except Exception:
        payload = raw_text
    if state == ToolResultState.ERROR:
        error = payload.get("error") if isinstance(payload, dict) else str(payload)
        return {"ok": False, "result": {}, "error": error}
    if isinstance(payload, dict) and {"ok", "result", "error"} <= set(payload.keys()):
        return {
            "ok": bool(payload.get("ok")),
            "result": payload.get("result") or {},
            "error": payload.get("error"),
        }
    return {"ok": True, "result": payload, "error": None}
