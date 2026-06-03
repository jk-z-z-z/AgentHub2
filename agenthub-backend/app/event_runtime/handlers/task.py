from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.types import MessageEventType
from app.services.group_task_service import assign_node_to_agent, claim_node, complete_node, mark_node_failed

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


async def handle_task_assigned(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    assign_node_to_agent(request.db, node_id=int(node_id), member_id=int(member_id))


async def handle_task_claimed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    claim_node(request.db, node_id=int(node_id), member_id=int(member_id))


async def handle_task_completed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    complete_node(
        request.db,
        node_id=int(node_id),
        member_id=int(member_id),
        output_summary=str(payload.get("output_summary") or ""),
    )


async def handle_task_failed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    if node_id is None:
        return
    mark_node_failed(request.db, node_id=int(node_id), error=str(payload.get("error") or ""))


TASK_EVENT_HANDLER_REGISTRY = {
    MessageEventType.Task.TASK_CREATED: _handle_noop,
    MessageEventType.Task.TASK_ASSIGNED: handle_task_assigned,
    MessageEventType.Task.TASK_CLAIMED: handle_task_claimed,
    MessageEventType.Task.TASK_COMPLETED: handle_task_completed,
    MessageEventType.Task.TASK_FAILED: handle_task_failed,
    MessageEventType.Task.TASK_REVIEWED: _handle_noop,
    MessageEventType.Task.TASK_REQUEUED: _handle_noop,
    MessageEventType.Task.NODE_EXEC_STARTED: _handle_noop,
    MessageEventType.Task.NODE_EXEC_FINISHED: _handle_noop,
}
