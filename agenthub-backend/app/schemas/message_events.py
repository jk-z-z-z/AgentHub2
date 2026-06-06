from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMBaseModel


class MessageEventOut(ORMBaseModel):
    id: str
    message_id: str
    run_id: str | None = None
    seq: int
    event_type: str
    category: str
    status: str
    payload_json: str
    created_at: datetime
    updated_at: datetime
