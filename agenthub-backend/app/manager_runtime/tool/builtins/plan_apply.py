from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.manager_planning_service import manager_tool_apply_plan


class PlanApplyTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.apply_plan"
        self.description = "Apply a structured plan to the DAG."
        self.input_schema = {
            "type": "object",
            "properties": {
                "group_id": {"type": "integer"},
                "actor_member_id": {"type": "integer"},
                "plan": {"type": "object"},
            },
            "required": ["group_id", "actor_member_id", "plan"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        group_id = kwargs.get("group_id")
        actor_member_id = kwargs.get("actor_member_id")
        plan = dict(kwargs.get("plan") or {})
        if group_id in (None, ""):
            return build_error_chunk("group_id_required")
        if actor_member_id in (None, ""):
            return build_error_chunk("actor_member_id_required")
        result = await manager_tool_apply_plan(
            self._db,
            group_id=int(group_id),
            creator_member_id=int(actor_member_id),
            plan=plan,
        )
        return build_tool_chunk(
            {
                "action": result.action,
                "group_id": int(group_id),
                "node_count": len(list(plan.get("nodes") or [])),
            }
        )
