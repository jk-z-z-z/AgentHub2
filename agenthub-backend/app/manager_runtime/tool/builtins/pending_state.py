from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk

from app.manager_runtime.assistant.state_store import (
    clear_pending_clarify,
    clear_pending_plan,
    load_pending_clarify,
    load_pending_plan,
    save_pending_clarify,
    save_pending_plan,
)
from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk


class PendingStateTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self) -> None:
        self.name = "manager.pending_state"
        self.description = "Load and update pending clarification or planning state."
        self.input_schema = {
            "type": "object",
            "properties": {
                "op": {"type": "string"},
                "group_id": {"type": "integer"},
                "context_key": {"type": "string"},
                "trigger_message_id": {"type": "integer"},
                "run_id": {"type": "integer"},
                "creator_member_id": {"type": "integer"},
                "goal_text": {"type": "string"},
                "questions": {"type": "array"},
                "plan": {"type": "object"},
            },
            "required": ["op", "group_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        op = str(kwargs.get("op") or "").strip()
        group_id = int(kwargs.get("group_id"))
        context_key = kwargs.get("context_key")
        trigger_message_id = kwargs.get("trigger_message_id")
        run_id = kwargs.get("run_id")
        if op == "load":
            return build_tool_chunk(
                {
                    "pending_plan": load_pending_plan(
                        group_id=group_id,
                        context_key=context_key,
                        trigger_message_id=trigger_message_id,
                    ),
                    "pending_clarify": load_pending_clarify(
                        group_id=group_id,
                        context_key=context_key,
                        trigger_message_id=trigger_message_id,
                    ),
                }
            )
        if op == "save_clarify":
            save_pending_clarify(
                group_id=group_id,
                creator_member_id=int(kwargs.get("creator_member_id")),
                goal_text=str(kwargs.get("goal_text") or ""),
                questions=list(kwargs.get("questions") or []),
                context_key=context_key,
                trigger_message_id=trigger_message_id,
                run_id=run_id,
            )
            return build_tool_chunk({"saved": True})
        if op == "save_plan":
            save_pending_plan(
                group_id=group_id,
                creator_member_id=int(kwargs.get("creator_member_id")),
                plan=dict(kwargs.get("plan") or {}),
                context_key=context_key,
                trigger_message_id=trigger_message_id,
                run_id=run_id,
            )
            return build_tool_chunk({"saved": True})
        if op == "clear_clarify":
            clear_pending_clarify(
                group_id=group_id,
                context_key=context_key,
                trigger_message_id=trigger_message_id,
            )
            return build_tool_chunk({"cleared": True})
        if op == "clear_plan":
            clear_pending_plan(
                group_id=group_id,
                context_key=context_key,
                trigger_message_id=trigger_message_id,
            )
            return build_tool_chunk({"cleared": True})
        return build_error_chunk("Unsupported op")
