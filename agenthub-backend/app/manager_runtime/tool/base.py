from __future__ import annotations

import json
from typing import Any

from agentscope.message import TextBlock, ToolResultState
from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import ToolChunk


def build_tool_chunk(payload: Any, *, ok: bool = True) -> ToolChunk:
    return ToolChunk(
        content=[TextBlock(text=json.dumps(payload, ensure_ascii=False, default=str))],
        state=ToolResultState.SUCCESS if ok else ToolResultState.ERROR,
    )


def build_error_chunk(error: str) -> ToolChunk:
    return build_tool_chunk({"error": error}, ok=False)


def permission_passthrough_decision() -> PermissionDecision:
    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No manager-specific permission override.",
        decision_reason="passthrough",
    )


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


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


class ManagerRuntimeContextMixin:
    def set_runtime_context(self, runtime_context: dict[str, Any] | None) -> None:
        self._runtime_context = dict(runtime_context or {})

    def _runtime_int(self, key: str) -> int | None:
        return _coerce_int(getattr(self, "_runtime_context", {}).get(key))

    def _runtime_str(self, key: str) -> str:
        value = getattr(self, "_runtime_context", {}).get(key)
        return str(value or "").strip()

    def _resolve_group_id(self, value: Any = None) -> int | None:
        return _coerce_int(value) or self._runtime_int("group_id") or self._runtime_int("project_id")

    def _resolve_creator_member_id(self, value: Any = None) -> int | None:
        return _coerce_int(value) or self._runtime_int("sender_id")

    def _resolve_trigger_message_id(self, value: Any = None) -> int | None:
        return (
            _coerce_int(value)
            or self._runtime_int("user_message_id")
            or self._runtime_int("source_message_id")
            or self._runtime_int("reply_to_message_id")
        )

    def _resolve_run_id(self, value: Any = None) -> int | None:
        run_id = _coerce_int(value) or self._runtime_int("run_id")
        if run_id is not None:
            return run_id

        group_id = self._resolve_group_id()
        trigger_message_id = self._resolve_trigger_message_id()
        if group_id is None or trigger_message_id is None:
            return None

        from app.manager_runtime.assistant.state_store import load_pending_clarify, load_pending_plan

        pending_items = [
            load_pending_plan(group_id=int(group_id), trigger_message_id=int(trigger_message_id)),
            load_pending_clarify(group_id=int(group_id), trigger_message_id=int(trigger_message_id)),
        ]
        for item in pending_items:
            if isinstance(item, dict):
                maybe_run_id = _coerce_int(item.get("run_id"))
                if maybe_run_id is not None:
                    return maybe_run_id
        return None

    def _list_group_runs(self) -> list[dict[str, Any]]:
        group_id = self._resolve_group_id()
        if group_id is None:
            return []

        from app.services.group_task_service import list_runs

        db = getattr(self, "_db", None)
        if db is None:
            return []
        rows = list_runs(db, group_id=int(group_id))
        return [
            {
                "run_id": int(row.id),
                "title": str(row.title or ""),
                "status": str(row.status or ""),
                "goal_text": str(row.goal_text or ""),
                "trigger_message_id": _coerce_int(getattr(row, "trigger_message_id", None)),
            }
            for row in rows
        ]

    def _default_title(self, value: Any = None) -> str:
        title = str(value or "").strip()
        if title:
            return title
        text = self._runtime_str("input_text") or self._runtime_str("goal_text")
        text = text[:80].strip()
        return text or "新任务流程图"

    def _default_goal_text(self, value: Any = None) -> str:
        goal_text = str(value or "").strip()
        if goal_text:
            return goal_text
        return self._runtime_str("input_text") or self._runtime_str("goal_text") or "请根据当前需求生成可执行任务流程图"
