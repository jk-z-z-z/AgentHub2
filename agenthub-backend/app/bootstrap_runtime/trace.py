from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.message_event_service import create_message_event


class BootstrapRuntimeTrace:
    def __init__(self, db: Session, *, message_id: int | None = None) -> None:
        self.db = db
        self.message_id = message_id

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.message_id is None:
            return
        create_message_event(
            self.db,
            message_id=int(self.message_id),
            event_type=str(event_type),
            payload=payload,
        )

    def emit_text(self, event_type: str, payload_text: str) -> None:
        self.emit(event_type, {"text": str(payload_text)})
