from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member
from app.models.message import Message
from app.core.config import settings
from app.services.context_builder import build_personal_system_prompt, build_project_system_prompt
from app.services.ai_service import ai_chat
from app.services.group_task_service import get_or_create_manager_member
from app.services.manager_planning_service import (
    manager_tool_build_plan_with_llm,
    manager_tool_read_group_memory_context,
    manager_tool_upsert_plan,
    save_pending_plan,
    load_pending_plan,
    clear_pending_plan,
)
from app.services.group_task_service import auto_assign_pending_nodes, list_group_task_nodes, run_agent_for_node
from app.services.memory_compressor_service import maybe_compress_project_memory
from app.ws.manager import ws_manager


def list_messages(db: Session, group_id: int, cursor: int | None = None, limit: int = 50) -> list[type[Message]]:
    query = db.query(Message).filter(Message.group_id == group_id)
    if cursor is not None:
        query = query.filter(Message.id < cursor)
    rows = query.order_by(Message.id.desc()).limit(min(limit, 100)).all()
    rows.reverse()
    return rows


def _build_short_term_history_msgs(db: Session, *, group_id: int, exclude_message_id: int | None = None) -> list:
    """
    Short-term memory: full chat context from DB messages.
    We load the last N messages and convert them into AgentScope Msg objects.
    """
    from agentscope.message import Msg

    raw = db.query(Message).filter(Message.group_id == int(group_id)).order_by(Message.id.asc()).all()
    out = []
    for item in raw:
        if exclude_message_id is not None and int(item.id) == int(exclude_message_id):
            continue
        role = "assistant" if str(item.message_type) == "ai" else "user"
        # Use member id as name for traceability.
        out.append(Msg(name=str(item.sender_member_id), role=role, content=[{"type": "text", "text": str(item.content or "")}]))
    return out


def _extract_agent_mentions(meta_json: str) -> list[int]:
    """
    Expected format (structured metadata):
      {"mentions":[{"kind":"agent","member_id":123}, ...]}
    Returns unique agent member_ids in order.
    """
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
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "agent":
            continue
        member_id = item.get("member_id")
        try:
            member_id_int = int(member_id)
        except (TypeError, ValueError):
            continue
        if member_id_int in seen:
            continue
        seen.add(member_id_int)
        out.append(member_id_int)
    return out


async def create_message(db: Session, group_id: int, sender_member_id: int, message_type: str, content: str, meta_json: str) -> Message:
    if not db.query(Group).filter(Group.id == group_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    member = db.query(Member).filter(Member.id == sender_member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender member not found")
    if member.group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender member does not belong to the group",
        )

    item = Message()
    item.group_id = group_id
    item.sender_member_id = sender_member_id
    item.message_type = message_type
    item.content = content
    item.metadata_json = meta_json
    # created_at/updated_at handled by SQLAlchemy defaults/onupdate

    db.add(item)
    db.commit()
    db.refresh(item)
    await ws_manager.broadcast(
        group_id,
        jsonable_encoder(
            {
                "event": "message.created",
                "data": {
                    "id": item.id,
                    "group_id": item.group_id,
                    "sender_member_id": item.sender_member_id,
                    "message_type": item.message_type,
                    "content": item.content,
                    "metadata_json": item.metadata_json,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                },
            }
        ),
    )
    return item


async def create_message_and_trigger_ai(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> Message:
    user_message = await create_message(db, group_id, sender_member_id, message_type, content, meta_json)

    sender = db.query(Member).filter(Member.id == sender_member_id).first()
    if not sender or sender.kind != "user":
        return user_message
    if message_type != "text":
        return user_message

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return user_message
    if group.type == "personal":
        # Personal conversations:
        # - do not support @mentions
        # - if members are (user, agent), auto-trigger the agent reply (no @ needed)
        if _extract_agent_mentions(meta_json):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Personal group does not support mentions",
            )
        # Find the single agent member in this group (if any)
        agent_member = (
            db.query(Member)
            .filter(Member.group_id == group_id, Member.kind == "agent")
            .order_by(Member.id.asc())
            .first()
        )
        # If personal is user+user, we simply store the message; no AI trigger.
        if not agent_member or not agent_member.agent_instance_id:
            return user_message

        agent = db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent:
            return user_message

        # The user identity for personal context comes from sender.user_ref
        if not sender.user_ref:
            return user_message
        try:
            user_id = int(sender.user_ref)
        except (TypeError, ValueError):
            return user_message

        system_prompt = build_personal_system_prompt(agent_id=int(agent.id), user_id=user_id)
        short_term = _build_short_term_history_msgs(db, group_id=int(group_id), exclude_message_id=int(user_message.id))
        reply_text = await ai_chat(
            content,
            system_prompt,
            agent_instance_id=int(agent.id),
            runtime_context={
                "group_type": "personal",
                "group_id": int(group_id),
                "user_id": int(user_id),
            },
            short_term_messages=short_term,
        )
        await create_message(
            db,
            group_id,
            int(agent_member.id),
            "ai",
            reply_text,
            json.dumps({"reply_to": str(user_message.id), "trigger": "personal_auto"}, ensure_ascii=False),
        )
        return user_message

    agent_member_ids = _extract_agent_mentions(meta_json)
    if not agent_member_ids:
        return user_message

    # Manager assistant trigger path:
    # if mentions include the configured manager member, create/advance a task run flow.
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    manager_member = None
    if cfg and int(cfg.enabled) == 1:
        manager_member = get_or_create_manager_member(db, group_id=int(group_id))
    if manager_member and int(manager_member.id) in {int(mid) for mid in agent_member_ids}:
        try:
            context = manager_tool_read_group_memory_context(db, group_id=int(group_id))
            short_term = _build_short_term_history_msgs(db, group_id=int(group_id), exclude_message_id=int(user_message.id))
            short_term_lines: list[str] = []
            for m in short_term[-20:]:
                text = ""
                content = getattr(m, "content", None)
                if isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict):
                        text = str(first.get("text", ""))
                    else:
                        text = str(getattr(first, "text", "") or "")
                short_term_lines.append(f"{getattr(m, 'name', 'user')}: {text}")
            short_term_text = "\n".join(short_term_lines)
            goal_text = str(content or "").strip()
            normalized = goal_text.strip().lower()
            pending = load_pending_plan(group_id=int(group_id))
            confirm_yes = {"确认", "同意", "通过", "approve", "yes", "ok", "可以"}
            if pending and normalized in confirm_yes:
                pending_creator = int(pending.get("creator_member_id") or 0)
                if pending_creator != int(sender_member_id):
                    manager_reply = "该规划草案仅允许发起人确认。请让发起人回复“确认”。"
                    await create_message(
                        db,
                        group_id,
                        int(manager_member.id),
                        "ai",
                        manager_reply,
                        json.dumps({"reply_to": str(user_message.id), "trigger": "manager_assistant"}, ensure_ascii=False),
                    )
                    return user_message
                plan = pending.get("plan") or {}
                creator_member_id = int(pending.get("creator_member_id") or sender_member_id)
                action, run = manager_tool_upsert_plan(
                    db,
                    group_id=int(group_id),
                    creator_member_id=creator_member_id,
                    trigger_message_id=int(user_message.id),
                    plan=plan,
                )
                clear_pending_plan(group_id=int(group_id))
                _ = auto_assign_pending_nodes(db, run_id=int(run.id))
                nodes = list_group_task_nodes(db, run_id=int(run.id))
                for n in nodes:
                    if n.status == "running" and n.assignee_kind == "agent":
                        try:
                            completed = await run_agent_for_node(db, node_id=int(n.id))
                            if completed and completed.manager_review_status == "pending":
                                pass
                        except Exception:
                            pass
                action_text = "已新建" if action == "created" else "已更新（仅未执行节点）"
                manager_reply = f"{action_text}并开始分配执行。\nrun_id={run.id}"
            else:
                plan = await manager_tool_build_plan_with_llm(
                    goal_text=goal_text,
                    context={**context, "short_term_preview": short_term_text[:4000]},
                )
                save_pending_plan(
                    group_id=int(group_id),
                    creator_member_id=int(sender_member_id),
                    goal_text=goal_text,
                    plan=plan,
                    ttl_seconds=int(settings.manager_plan_ttl_seconds),
                )
                manager_reply = (
                    "我已生成规划草案（已按当前目标校正），请确认是否落库执行（回复：确认 / 同意）。\n\n"
                    "```json\n"
                    f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n"
                    "```"
                )
        except Exception as e:
            manager_reply = (
                "我已收到任务请求，但本次落库失败。\n"
                f"错误：{str(e)}\n"
                "请检查群管家是否启用、会话是否为项目组，然后重试 @管家。"
            )
        await create_message(
            db,
            group_id,
            int(manager_member.id),
            "ai",
            manager_reply,
            json.dumps({"reply_to": str(user_message.id), "trigger": "manager_assistant"}, ensure_ascii=False),
        )
        return user_message

    async def _reply_for_agent_member(agent_member_id: int) -> None:
        if manager_member and int(agent_member_id) == int(manager_member.id):
            return
        agent_member = db.query(Member).filter(Member.id == agent_member_id).first()
        if not agent_member or agent_member.kind != "agent":
            return
        if int(agent_member.group_id) != int(group_id):
            return
        if not agent_member.agent_instance_id:
            return
        agent = db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent:
            return

        # Keep project long-term memory (MEMORY.md) up to date via token-based compression.
        try:
            await maybe_compress_project_memory(
                db,
                project_id=int(group_id),
                agent_id=int(agent.id),
            )
        except Exception:
            # Compressor failure should not block normal chat.
            pass

        system_prompt = build_project_system_prompt(agent_id=int(agent.id), project_id=int(group_id))
        short_term = _build_short_term_history_msgs(db, group_id=int(group_id), exclude_message_id=int(user_message.id))
        reply_text = await ai_chat(
            content,
            system_prompt,
            agent_instance_id=int(agent.id),
            runtime_context={
                "group_type": "project",
                "group_id": int(group_id),
                "user_id": int(sender.user_ref) if sender and sender.user_ref else None,
            },
            short_term_messages=short_term,
        )
        await create_message(
            db,
            group_id,
            int(agent_member.id),
            "ai",
            reply_text,
            json.dumps({"reply_to": str(user_message.id), "trigger": "mention"}, ensure_ascii=False),
        )

    await asyncio.gather(*[_reply_for_agent_member(mid) for mid in agent_member_ids])
    return user_message
