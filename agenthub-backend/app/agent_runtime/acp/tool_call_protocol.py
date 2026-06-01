from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ToolCallSpec:
    tool_code: str
    args: dict


def extract_tool_calls(text: str) -> list[ToolCallSpec]:
    raw = str(text or "").strip()
    if not raw:
        return []
    candidate = None
    if "```" in raw:
        for block in raw.split("```"):
            b = block.strip()
            if b.startswith("json"):
                b = b[4:].strip()
            if b.startswith("{") and b.endswith("}"):
                candidate = b
                break
    if candidate is None and raw.startswith("{") and raw.endswith("}"):
        candidate = raw
    if candidate is None:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            candidate = raw[start : end + 1]
    if not candidate:
        return []
    try:
        obj = json.loads(candidate)
    except Exception:
        return []
    if not isinstance(obj, dict):
        return []
    calls = obj.get("tool_calls") or obj.get("toolCalls") or []
    if not isinstance(calls, list):
        return []
    out: list[ToolCallSpec] = []
    for c in calls:
        if not isinstance(c, dict):
            continue
        tool_code = str(c.get("tool_code") or c.get("toolCode") or "").strip()
        if not tool_code:
            continue
        args = c.get("args") if isinstance(c.get("args"), dict) else {}
        out.append(ToolCallSpec(tool_code=tool_code, args=dict(args)))
    return out


def build_tool_result_message(*, tool_code: str, ok: bool, result: dict) -> str:
    payload = {"tool_code": tool_code, "ok": bool(ok), "result": result}
    return json.dumps(payload, ensure_ascii=False)

