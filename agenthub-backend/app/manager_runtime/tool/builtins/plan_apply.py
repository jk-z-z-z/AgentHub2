from __future__ import annotations

from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import ManagerTool, ToolCallResult
from app.services.group_task.orchestration.orchestrator_service import apply_plan_and_schedule
from app.manager_runtime.assistant.planning import manager_tool_upsert_plan


class PlanApplyTool(ManagerTool):
    code = "manager.apply_plan"

    def __init__(self, *, db: Session) -> None:
        self._db = db

    async def __call__(self, **kwargs) -> ToolCallResult:
        group_id = int(kwargs.get("group_id"))
        actor_member_id = int(kwargs.get("actor_member_id"))
        trigger_message_id = int(kwargs.get("trigger_message_id"))
        plan = dict(kwargs.get("plan") or {})
        action, run = manager_tool_upsert_plan(
            self._db,
            group_id=group_id,
            creator_member_id=actor_member_id,
            trigger_message_id=trigger_message_id,
            plan=plan,
        )
        result = await apply_plan_and_schedule(
            self._db,
            run_id=int(run.id),
            plan=plan,
            actor_member_id=actor_member_id,
        )
        return ToolCallResult(
            ok=True,
            result={
                "action": action,
                "run_id": int(result.run_id),
                "scheduled_count": int(result.scheduled_count),
            },
        )
