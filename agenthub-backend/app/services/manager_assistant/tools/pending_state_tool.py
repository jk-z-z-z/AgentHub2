from __future__ import annotations

from app.services.manager_assistant.state_store import (
    clear_pending_clarify,
    clear_pending_plan,
    load_pending_clarify,
    load_pending_plan,
    save_pending_clarify,
    save_pending_plan,
)
from app.services.manager_assistant.tools.base import ManagerTool, ToolCallResult


class PendingStateTool(ManagerTool):
    code = "manager.pending_state"

    async def __call__(self, **kwargs) -> ToolCallResult:
        op = str(kwargs.get("op") or "").strip()
        group_id = int(kwargs.get("group_id"))
        if op == "load":
            return ToolCallResult(
                ok=True,
                result={
                    "pending_plan": load_pending_plan(group_id=group_id),
                    "pending_clarify": load_pending_clarify(group_id=group_id),
                },
            )
        if op == "save_clarify":
            save_pending_clarify(
                group_id=group_id,
                creator_member_id=int(kwargs.get("creator_member_id")),
                goal_text=str(kwargs.get("goal_text") or ""),
                questions=list(kwargs.get("questions") or []),
            )
            return ToolCallResult(ok=True, result={"saved": True})
        if op == "save_plan":
            save_pending_plan(
                group_id=group_id,
                creator_member_id=int(kwargs.get("creator_member_id")),
                plan=dict(kwargs.get("plan") or {}),
            )
            return ToolCallResult(ok=True, result={"saved": True})
        if op == "clear_clarify":
            clear_pending_clarify(group_id=group_id)
            return ToolCallResult(ok=True, result={"cleared": True})
        if op == "clear_plan":
            clear_pending_plan(group_id=group_id)
            return ToolCallResult(ok=True, result={"cleared": True})
        return ToolCallResult(ok=False, result={}, error="Unsupported op")

