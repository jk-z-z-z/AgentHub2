from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.event_runtime.context import (
    EventDispatchRequest,
    broadcast_reply_failed,
    done_trigger_event,
    failed_trigger_event,
    resolve_trigger_event,
)
from app.event_runtime.facade import list_message_events
from app.event_runtime.handlers import EVENT_HANDLER_REGISTRY


EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def dispatch_message_event(request: EventDispatchRequest) -> None:
    event = resolve_trigger_event(request.db, message_id=int(request.message_id), event_id=request.event_id)
    if event is None:
        return
    handler = EVENT_HANDLER_REGISTRY.get(str(event.event_type))
    if handler is None:
        done_trigger_event(request.db, event_id=int(event.id))
        return
    try:
        await handler(request, event)
        done_trigger_event(request.db, event_id=int(event.id))
    except Exception as exc:
        failed_trigger_event(request.db, event_id=int(event.id), error=str(exc))
        if str(event.event_type) == "message.created":
            await broadcast_reply_failed(
                group_id=int(request.group_id),
                message_id=int(request.message_id),
                sender_member_id=int(request.sender_member_id),
                error=str(exc),
            )
        raise


async def dispatch_message_event_chain(request: EventDispatchRequest, *, max_passes: int = 32) -> None:
    processed_event_ids: set[int] = set()
    for _ in range(max_passes):
        events = list_message_events(request.db, message_id=int(request.message_id))
        pending_events = [
            event
            for event in events
            if int(event.id) not in processed_event_ids and str(event.status) == "pending"
        ]
        if not pending_events:
            return
        progressed = False
        for event in pending_events:
            if int(event.id) in processed_event_ids:
                continue
            progressed = True
            processed_event_ids.add(int(event.id))
            await dispatch_message_event(
                EventDispatchRequest(
                    db=request.db,
                    group_id=int(request.group_id),
                    sender_member_id=int(request.sender_member_id),
                    message_id=int(request.message_id),
                    message_type=str(request.message_type),
                    content=str(request.content),
                    meta_json=str(request.meta_json),
                    event_id=int(event.id),
                )
            )
        if not progressed:
            return
