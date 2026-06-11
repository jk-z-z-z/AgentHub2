from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentscope.skill import LocalSkillLoader
from agentscope.tool import Toolkit
from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.services.storage_init_service import ensure_runtime_personal, ensure_user_space
from app.services.storage_paths import agent_dir, user_dir
from app.bootstrap_runtime.skill import load_bootstrap_skill_loaders
from app.bootstrap_runtime.tool import load_bootstrap_toolkit


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def _extract_agent_mentions(meta_json: str) -> list[int]:
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


def _normalize_short_term_memory(short_term_memory: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in short_term_memory or []:
        if isinstance(item, dict):
            normalized.append(
                {
                    "role": str(item.get("role", "user")),
                    "content": item.get("content", ""),
                    "name": item.get("name"),
                }
            )
            continue
        normalized.append(
            {
                "role": str(getattr(item, "role", "user")),
                "content": getattr(item, "content", ""),
                "name": getattr(item, "name", None),
            }
        )
    return normalized


def _build_bootstrap_system_prompt(*, agent_id: int, user_id: int) -> str:
    ensure_user_space(int(user_id))
    ensure_runtime_personal(int(agent_id), int(user_id))
    soul = _read_text(agent_dir(int(agent_id)) / "SOUL.md")
    profile_md = _read_text(agent_dir(int(agent_id)) / "PROFILE.md")
    bootstrap = _read_text(agent_dir(int(agent_id)) / "BOOTSTRAP.md")
    user_profile = _read_text(user_dir(int(user_id)) / "PROFILE.md")
    user_memory = _read_text(user_dir(int(user_id)) / "MEMORY.md")
    parts: list[str] = []
    if soul.strip():
        parts.append("# Agent SOUL\n" + soul.strip())
    if profile_md.strip():
        parts.append("# Agent PROFILE\n" + profile_md.strip())
    if bootstrap.strip():
        parts.append("# Agent BOOTSTRAP\n" + bootstrap.strip())
    parts.append(
        "# Role\n"
        "你正在执行 bootstrap，优先遵循已挂载的 bootstrap skill 和工具完成工作区初始化。"
    )
    if user_profile.strip():
        parts.append("# User PROFILE\n" + user_profile.strip())
    if user_memory.strip():
        parts.append("# User MEMORY\n" + user_memory.strip())
    return "\n\n".join(parts).strip()


@dataclass
class BuiltBootstrap:
    group: Group
    sender: Member
    user_message: Message
    agent_member: Member
    agent: AgentInstance
    user_id: int
    system_prompt: str
    runtime_context: dict[str, Any]
    short_term_memory: list[dict[str, Any]]
    skill_loaders: list[LocalSkillLoader]
    toolkit: Toolkit
    engine_type: str


def build_complete_bootstrap(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    user_message_id: int,
    content: str,
    meta_json: str,
    short_term_memory: list[dict[str, Any]] | list[Any],
    extra_context: dict[str, Any] | None = None,
) -> BuiltBootstrap | None:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    sender = db.query(Member).filter(Member.id == int(sender_member_id)).first()
    user_message = db.query(Message).filter(Message.id == int(user_message_id)).first()
    if not group or not sender or not user_message:
        return None
    if _extract_agent_mentions(meta_json):
        raise ValueError("Bootstrap group does not support mentions")
    agent_member = (
        db.query(Member)
        .filter(Member.group_id == int(group.id), Member.kind == "agent")
        .order_by(Member.id.asc())
        .first()
    )
    if not agent_member or not agent_member.agent_instance_id or not sender.user_ref:
        return None
    try:
        user_id = int(sender.user_ref)
    except (TypeError, ValueError):
        return None
    agent = db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
    if not agent:
        return None
    runtime_context = {
        **dict(extra_context or {}),
        "group_type": "bootstrap",
        "group_id": int(group.id),
        "user_id": int(user_id),
        "input_text": str(content or ""),
    }
    return BuiltBootstrap(
        group=group,
        sender=sender,
        user_message=user_message,
        agent_member=agent_member,
        agent=agent,
        user_id=int(user_id),
        system_prompt=_build_bootstrap_system_prompt(agent_id=int(agent.id), user_id=int(user_id)),
        runtime_context=runtime_context,
        short_term_memory=_normalize_short_term_memory(short_term_memory),
        skill_loaders=load_bootstrap_skill_loaders(),
        toolkit=load_bootstrap_toolkit(
            int(agent.id),
            runtime_context=runtime_context,
        ),
        engine_type=str(getattr(agent, "engine_type", "agentscope_react") or "agentscope_react").strip().lower(),
    )
