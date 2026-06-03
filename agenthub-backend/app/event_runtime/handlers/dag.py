from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.types import MessageEventType
from app.services.group_task_service import create_nodes, patch_dag, update_node_status

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


async def handle_dag_created(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    nodes = payload.get("nodes")
    creator_member_id = payload.get("creator_member_id")
    if isinstance(nodes, list) and creator_member_id is not None:
        create_nodes(request.db, group_id=int(request.group_id), creator_member_id=int(creator_member_id), nodes=nodes)


async def handle_dag_updated(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    ops = payload.get("ops")
    if isinstance(ops, list):
        patch_dag(request.db, group_id=int(request.group_id), ops=ops)


async def handle_dag_node_status_changed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    if node_id is None:
        return
    update_node_status(
        request.db,
        node_id=int(node_id),
        status_value=str(payload.get("status") or "pending"),
        output_summary=payload.get("output_summary"),
        error=payload.get("error"),
    )


DAG_EVENT_HANDLER_REGISTRY = {
    MessageEventType.Dag.DAG_CREATED: handle_dag_created,
    MessageEventType.Dag.DAG_UPDATED: handle_dag_updated,
    MessageEventType.Dag.DAG_PATCHED: handle_dag_updated,
    MessageEventType.Dag.NODE_CREATED: _handle_noop,
    MessageEventType.Dag.NODE_UPDATED: _handle_noop,
    MessageEventType.Dag.NODE_DELETED: _handle_noop,
    MessageEventType.Dag.EDGE_CREATED: _handle_noop,
    MessageEventType.Dag.EDGE_DELETED: _handle_noop,
    MessageEventType.Dag.NODE_STATUS_CHANGED: handle_dag_node_status_changed,
    MessageEventType.Dag.PLANNING_STARTED: _handle_noop,
    MessageEventType.Dag.PLANNING_FINISHED: _handle_noop,
}
