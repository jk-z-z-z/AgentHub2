from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.group_task.node_service import auto_assign_pending_nodes, list_group_task_nodes, run_agent_for_node


async def trigger_ready_agent_nodes(db: Session, *, run_id: int) -> int:
    _ = auto_assign_pending_nodes(db, run_id=int(run_id))
    nodes = list_group_task_nodes(db, run_id=int(run_id))
    started = 0
    for node in nodes:
        if node.status == "running" and node.assignee_kind == "agent":
            try:
                await run_agent_for_node(db, node_id=int(node.id))
                started += 1
            except Exception:
                pass
    return started
