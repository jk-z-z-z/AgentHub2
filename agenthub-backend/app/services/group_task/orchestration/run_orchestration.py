from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.group_orchestrator.scheduler import run_ready_nodes_parallel


async def trigger_ready_agent_nodes(db: Session, *, run_id: int) -> int:
    return await run_ready_nodes_parallel(db, run_id=int(run_id), max_concurrency=20)
