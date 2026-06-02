from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services.message_event_service import create_message_event


@dataclass
class ManagerRuntimeTrace:
    db: Session
    message_id: int | None = None

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if self.message_id is None:
            return
        create_message_event(
            self.db,
            message_id=int(self.message_id),
            event_type=str(event_type),
            payload=payload or {},
        )
