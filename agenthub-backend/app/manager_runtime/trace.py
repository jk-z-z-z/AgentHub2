from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.event_runtime.types import MessageEventType
from app.event_runtime.facade import create_message_event


@dataclass
class ManagerRuntimeTrace:
    db: Session
    message_id: int | None = None
    run_id: int | None = None

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if self.message_id is None:
            return
        event_payload = dict(payload or {})
        if self.run_id is not None and "run_id" not in event_payload:
            event_payload["run_id"] = int(self.run_id)
        create_message_event(
            self.db,
            message_id=int(self.message_id),
            event_type=str(event_type),
            payload=event_payload,
            run_id=int(self.run_id) if self.run_id is not None else None,
        )

    def emit_run_started(self, payload: dict[str, Any] | None = None) -> None:
        self.emit(MessageEventType.Execution.RUN_STARTED, payload)

    def emit_run_finished(self, payload: dict[str, Any] | None = None) -> None:
        self.emit(MessageEventType.Execution.RUN_FINISHED, payload)

    def emit_tool_call(self, payload: dict[str, Any] | None = None) -> None:
        self.emit(MessageEventType.Execution.TOOL_CALL, payload)

    def emit_tool_result(self, payload: dict[str, Any] | None = None) -> None:
        self.emit(MessageEventType.Execution.TOOL_RESULT, payload)
