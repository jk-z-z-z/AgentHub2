from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.types import MessageEventType
from app.models.message_event import MessageEvent
from app.services.group_task_service import create_run, patch_dag, replace_run_nodes, update_node_status

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


def _payload_as_dict(event: Any | None) -> dict[str, Any]:
    payload = getattr(event, "payload", None) if event is not None else None
    return payload if isinstance(payload, dict) else {}


def _payload_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _attach_event_run(event: Any | None, *, run_id: int) -> None:
    if not isinstance(event, MessageEvent):
        return
    payload = event.payload
    payload["run_id"] = int(run_id)
    event.run_id = int(run_id)
    event.payload_json = json.dumps(payload, ensure_ascii=False)
    event.updated_at = event.updated_at


async def handle_dag_created(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return
    run_id = _payload_int(payload, "run_id")
    if run_id is not None:
        replace_run_nodes(request.db, run_id=int(run_id), nodes=nodes)
        return
    group_id = _payload_int(payload, "group_id")
    creator_member_id = _payload_int(payload, "creator_member_id")
    title = str(payload.get("title") or "").strip()
    goal_text = str(payload.get("goal_text") or payload.get("goal") or "").strip()
    if group_id is None or creator_member_id is None or not title or not goal_text:
        return
    run = create_run(
        request.db,
        group_id=int(group_id),
        creator_member_id=int(creator_member_id),
        title=title,
        goal_text=goal_text,
        nodes=nodes,
        trigger_message_id=int(request.message_id),
    )
    _attach_event_run(event, run_id=int(run.id))
    request.db.add(event)
    request.db.commit()


async def handle_dag_updated(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    ops = payload.get("ops")
    run_id = _payload_int(payload, "run_id")
    if isinstance(ops, list) and run_id is not None:
        patch_dag(request.db, run_id=int(run_id), ops=ops)


async def handle_dag_node_status_changed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
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
