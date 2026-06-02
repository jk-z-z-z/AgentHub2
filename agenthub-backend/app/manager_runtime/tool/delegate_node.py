from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.group_task.node_service import run_agent_for_node
from app.manager_runtime.tool.base import ManagerTool, ToolCallResult


class DelegateNodeTool(ManagerTool):
    code = "manager.delegate_node"

    def __init__(self, *, db: Session) -> None:
        self._db = db

    async def __call__(self, **kwargs) -> ToolCallResult:
        node_id = int(kwargs.get("node_id"))
        node = await run_agent_for_node(self._db, node_id=node_id)
        if not node:
            return ToolCallResult(ok=False, result={}, error="node_not_found_or_not_runnable")
        return ToolCallResult(
            ok=True,
            result={
                "node_id": int(node.id),
                "run_id": int(node.run_id),
                "status": str(node.status),
                "assignee_member_id": int(node.assignee_member_id) if node.assignee_member_id else None,
                "output_summary": str(node.output_summary or ""),
            },
        )
