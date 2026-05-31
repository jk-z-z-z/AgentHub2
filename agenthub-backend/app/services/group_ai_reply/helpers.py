from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.message import Message


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


def build_short_term_history_msgs(db: Session, *, group_id: int, exclude_message_id: int | None = None) -> list:
    from agentscope.message import Msg

    raw = db.query(Message).filter(Message.group_id == int(group_id)).order_by(Message.id.asc()).all()
    out = []
    for item in raw:
        if exclude_message_id is not None and int(item.id) == int(exclude_message_id):
            continue
        role = "assistant" if str(item.message_type) == "ai" else "user"
        out.append(Msg(name=str(item.sender_member_id), role=role, content=[{"type": "text", "text": str(item.content or "")}]))
    return out
