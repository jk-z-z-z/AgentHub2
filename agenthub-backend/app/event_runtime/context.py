from __future__ import annotations

import json
from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.agent_runtime.message_store import create_message, update_message, create_pending_ai_message
from app.event_runtime.facade import build_group_short_term_memory_from_events, create_message_event, list_message_events, update_message_event_status
from app.event_runtime.types import MessageEventStatus, MessageEventType
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member
from app.models.message import Message
from app.ws_runtime import WsEventType, ws_manager


@dataclass
class EventDispatchRequest:
    db: Session
    group_id: int
    sender_member_id: int
    message_id: int
    message_type: str
    content: str
    meta_json: str
    event_id: int | None = None


def get_or_create_manager_member(db: Session, *, group_id: int) -> Member:
    row = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "system", Member.display_name == "管家")
        .first()
    )
    if row:
        return row
    row = Member(
        group_id=int(group_id),
        kind="system",
        display_name="管家",
        user_ref=None,
        agent_instance_id=None,
        title="group-manager",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def project_manager_enabled(db: Session, *, group_id: int) -> bool:
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    return bool(cfg and int(cfg.enabled) == 1)


def build_reply_context(db: Session, *, group_id: int, sender_member_id: int, message_id: int) -> tuple[Group, Member, Message] | None:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    sender = db.query(Member).filter(Member.id == int(sender_member_id)).first()
    user_message = db.query(Message).filter(Message.id == int(message_id)).first()
    if not group or not sender or not user_message:
        return None
    return group, sender, user_message


def build_short_term_memory(db: Session, *, group_id: int, exclude_message_id: int | None = None, limit: int = 80) -> list[dict[str, object]]:
    return build_group_short_term_memory_from_events(
        db,
        group_id=int(group_id),
        exclude_message_id=exclude_message_id,
        limit_messages=int(limit),
    )


def extract_agent_mentions(meta_json: str) -> list[int]:
    try:
        payload = json.loads(meta_json or "{}")
    except Exception:
        return []
    mentions = payload.get("mentions")
    if not isinstance(mentions, list):
        return []
    out: list[int] = []
    seen: set[int] = set()
    for item in mentions:
        if not isinstance(item, dict) or item.get("kind") != "agent":
            continue
        try:
            member_id = int(item.get("member_id"))
        except (TypeError, ValueError):
            continue
        if member_id in seen:
            continue
        seen.add(member_id)
        out.append(member_id)
    return out


async def broadcast_reply_failed(*, group_id: int, message_id: int, sender_member_id: int, error: str) -> None:
    await ws_manager.broadcast(
        int(group_id),
        jsonable_encoder(
            {
                "event": WsEventType.REPLY_FAILED,
                "data": {
                    "group_id": int(group_id),
                    "message_id": int(message_id),
                    "sender_member_id": int(sender_member_id),
                    "error": str(error),
                },
            }
        ),
    )


async def mark_failed_reply(ai_message: Message, *, reply_to_message_id: int, trigger: str, db: Session) -> None:
    await update_message(
        db,
        message_id=int(ai_message.id),
        content="AI 回复失败，请稍后重试。",
        meta_json=f'{{"reply_to":"{int(reply_to_message_id)}","trigger":"{trigger}","status":"failed"}}',
    )
    create_message_event(
        db,
        message_id=int(ai_message.id),
        event_type=MessageEventType.InputOutput.REPLY_FAILED,
        payload={
            "reply_to_message_id": int(reply_to_message_id),
            "trigger": str(trigger),
            "status": "failed",
        },
    )


def resolve_trigger_event(db: Session, *, message_id: int, event_id: int | None = None):
    events = list_message_events(db, message_id=int(message_id))
    if not events:
        return None
    if event_id is None:
        return events[-1]
    for event in events:
        if int(event.id) == int(event_id):
            return event
    return None


def done_trigger_event(db: Session, *, event_id: int) -> None:
    update_message_event_status(db, event_id=int(event_id), status=MessageEventStatus.DONE)


def failed_trigger_event(db: Session, *, event_id: int, error: str) -> None:
    update_message_event_status(
        db,
        event_id=int(event_id),
        status=MessageEventStatus.FAILED,
        payload={"error": str(error)},
    )
