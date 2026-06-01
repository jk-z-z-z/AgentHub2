from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.group_orchestrator.assignment_service import smart_auto_assign_pending_nodes
from app.services.group_task.node_service import auto_assign_pending_nodes, list_group_task_nodes, run_agent_for_node


async def run_ready_nodes_parallel(db: Session, *, run_id: int, max_concurrency: int = 20) -> int:
    """
    Dispatch all runnable agent nodes with a soft concurrency cap.

    Notes:
    - SQLAlchemy Session is not concurrency-safe. Each concurrent node run uses its own Session.
    - We loop until no more runnable agent nodes exist, so newly-unblocked nodes can start.
    """
    total_ok = 0
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))

    while True:
        # First try smart assignment (LLM assisted), then fallback to exact-match assignment.
        try:
            _ = await smart_auto_assign_pending_nodes(db, run_id=int(run_id))
        except Exception:
            pass
        _ = auto_assign_pending_nodes(db, run_id=int(run_id))
        nodes = list_group_task_nodes(db, run_id=int(run_id))
        targets = [n for n in nodes if n.status == "running" and n.assignee_kind == "agent"]
        if not targets:
            break

        async def _run_one(node_id: int) -> bool:
            async with sem:
                local_db = SessionLocal()
                try:
                    await run_agent_for_node(local_db, node_id=int(node_id))
                    return True
                except Exception:
                    return False
                finally:
                    local_db.close()

        results = await asyncio.gather(*[_run_one(int(n.id)) for n in targets], return_exceptions=False)
        total_ok += sum(1 for r in results if r)

        # Refresh outer session state to observe node transitions and newly-ready nodes.
        try:
            db.expire_all()
        except Exception:
            pass

    return int(total_ok)
