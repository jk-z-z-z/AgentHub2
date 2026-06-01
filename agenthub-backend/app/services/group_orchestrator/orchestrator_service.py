from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.event_types import GroupTaskEventType
from app.models.group_task_run import GroupTaskRun
from app.services.group_task.event_service import log_group_task_event
from app.services.group_task.node_service import (
    auto_assign_pending_nodes,
    get_group_task_run,
    list_group_task_nodes,
    update_group_task_dag,
)
from app.services.group_task.orchestration.run_orchestration import trigger_ready_agent_nodes


@dataclass(frozen=True)
class OrchestratorResult:
    run_id: int
    action: str
    scheduled_count: int


def _is_not_started(node_status: str) -> bool:
    return str(node_status or "") in {"pending", "blocked"}


def _plan_nodes(plan: dict) -> list[dict]:
    nodes = plan.get("nodes") if isinstance(plan, dict) else None
    return list(nodes or []) if isinstance(nodes, list) else []


async def apply_plan_and_schedule(
    db: Session,
    *,
    run_id: int,
    plan: dict,
    actor_member_id: int,
) -> OrchestratorResult:
    """
    Apply a manager plan to the active run (only modifying not-started nodes),
    persist a new graph snapshot/version, then schedule runnable agent nodes.
    """
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise ValueError("Run not found")

    before_nodes = list_group_task_nodes(db, run_id=int(run.id))
    before_keys = {n.node_key: n for n in before_nodes}

    updated = update_group_task_dag(db, run_id=int(run.id), nodes=_plan_nodes(plan))

    after_nodes = list_group_task_nodes(db, run_id=int(updated.id))
    after_keys = {n.node_key: n for n in after_nodes}

    changed_not_started: list[str] = []
    for k, after in after_keys.items():
        before = before_keys.get(k)
        if before is None and _is_not_started(after.status):
            changed_not_started.append(k)
            continue
        if before is None:
            continue
        if not _is_not_started(before.status):
            continue
        if (before.title, before.detail, before.deps_json, before.role_required) != (
            after.title,
            after.detail,
            after.deps_json,
            after.role_required,
        ):
            changed_not_started.append(k)

    log_group_task_event(
        db,
        run_id=int(updated.id),
        node_id=None,
        event_type=GroupTaskEventType.ORCHESTRATOR_PLAN_APPLIED,
        payload={
            "actor_member_id": int(actor_member_id),
            "changed_not_started_node_keys": changed_not_started[:80],
            "node_count": len(after_nodes),
        },
    )

    # Auto-assign + schedule runnable agent nodes.
    _ = auto_assign_pending_nodes(db, run_id=int(updated.id))
    scheduled = await trigger_ready_agent_nodes(db, run_id=int(updated.id))
    return OrchestratorResult(run_id=int(updated.id), action="applied", scheduled_count=int(scheduled))


async def schedule_ready_nodes(db: Session, *, run_id: int) -> int:
    """
    Convenience entrypoint used by API/jobs: auto-assign then schedule runnable nodes.
    """
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        return 0
    _ = auto_assign_pending_nodes(db, run_id=int(run.id))
    return await trigger_ready_agent_nodes(db, run_id=int(run.id))

