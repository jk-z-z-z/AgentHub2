from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.event_runtime.context import EventDispatchRequest
from app.event_runtime.types import MessageEventType

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


SYSTEM_EVENT_HANDLER_REGISTRY = {
    MessageEventType.System.BOOTSTRAP_STARTED: _handle_noop,
    MessageEventType.System.BOOTSTRAP_FINISHED: _handle_noop,
    MessageEventType.System.BOOTSTRAP_FAILED: _handle_noop,
    MessageEventType.System.MEMORY_COMPRESSION_STARTED: _handle_noop,
    MessageEventType.System.MEMORY_COMPRESSION_FINISHED: _handle_noop,
}
