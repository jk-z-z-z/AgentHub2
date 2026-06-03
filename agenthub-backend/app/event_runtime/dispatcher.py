from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.event_runtime.context import (
    EventDispatchRequest,
    broadcast_reply_failed,
    done_trigger_event,
    failed_trigger_event,
    resolve_trigger_event,
)
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
