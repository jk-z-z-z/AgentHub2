from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message

EmitMessage = Callable[[Session, int, int, str, str, str], Awaitable[Message]]


@dataclass
class ReplyContext:
    db: Session
    group: Group
    sender: Member
    user_message: Message
    content: str
    meta_json: str
    emit_message: EmitMessage
    ai_message: Message | None = None
