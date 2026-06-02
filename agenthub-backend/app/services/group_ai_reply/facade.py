from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.agent_runtime import invoke_agent
from app.agent_runtime.message_store import create_pending_ai_message
from app.bootstrap_runtime import invoke_bootstrap
from app.common.event_types import WsEventType
from app.manager_runtime import invoke_manager
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.member import Member
from app.models.message import Message
from app.services.group_ai_reply.reply_utils import emit_ai_reply
from app.services.group_task.manager_service import get_or_create_manager_member
from app.services.memory_compressor_service import maybe_compress_project_memory
from app.agent_runtime.message_store import update_message
from app.ws.manager import ws_manager


@dataclass
class GroupAIReplyRequest:
    db: Session
    group_id: int
    sender_member_id: int
    user_message_id: int
    message_type: str
    content: str
    meta_json: str


def _build_reply_context(db: Session, *, group_id: int, sender_member_id: int, user_message_id: int) -> tuple[Group, Member, Message] | None:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    sender = db.query(Member).filter(Member.id == int(sender_member_id)).first()
    user_message = db.query(Message).filter(Message.id == int(user_message_id)).first()
    if not group or not sender or not user_message:
        return None
    return group, sender, user_message


def _build_short_term_memory(db: Session, *, group_id: int, exclude_message_id: int | None = None, limit: int = 80) -> list[dict[str, str]]:
    history = (
        db.query(Message)
        .filter(Message.group_id == int(group_id))
        .order_by(Message.id.desc())
        .limit(int(limit) + 10)
        .all()
    )
    history.reverse()
    output: list[dict[str, str]] = []
    for item in history:
        if exclude_message_id is not None and int(item.id) == int(exclude_message_id):
            continue
        role = "assistant" if str(item.message_type) == "ai" else "user"
        output.append({"role": role, "content": str(item.content or ""), "name": str(item.sender_member_id)})
    return output


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


async def _broadcast_reply_failed(*, group_id: int, user_message_id: int, sender_member_id: int, error: str) -> None:
    await ws_manager.broadcast(
        int(group_id),
        jsonable_encoder(
            {
                "event": WsEventType.REPLY_FAILED,
                "data": {
                    "group_id": int(group_id),
                    "message_id": int(user_message_id),
                    "sender_member_id": int(sender_member_id),
                    "error": str(error),
                },
            }
        ),
    )


async def _mark_failed_reply(ai_message: Message, *, reply_to_message_id: int, trigger: str, db: Session) -> None:
    await update_message(
        db,
        message_id=int(ai_message.id),
        content="AI 回复失败，请稍后重试。",
        meta_json=f'{{"reply_to":"{int(reply_to_message_id)}","trigger":"{trigger}","status":"failed"}}',
    )


async def _handle_bootstrap(ctx_db: Session, group: Group, sender: Member, user_message: Message, content: str, meta_json: str) -> None:
    if _extract_agent_mentions(meta_json):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bootstrap group does not support mentions")
    await invoke_bootstrap(
        ctx_db,
        group_id=int(group.id),
        sender_member_id=int(sender.id),
        user_message_id=int(user_message.id),
        content=content,
        meta_json=meta_json,
        short_term_memory=_build_short_term_memory(ctx_db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
        extra_context={
            "group_type": "bootstrap",
            "group_id": int(group.id),
            "user_id": int(sender.user_ref) if sender.user_ref else None,
            "input_text": str(content or ""),
        },
    )


async def _handle_personal(ctx_db: Session, group: Group, sender: Member, user_message: Message, content: str, meta_json: str) -> None:
    if _extract_agent_mentions(meta_json):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Personal group does not support mentions")
    agent_member = (
        ctx_db.query(Member)
        .filter(Member.group_id == int(group.id), Member.kind == "agent")
        .order_by(Member.id.asc())
        .first()
    )
    if not agent_member or not agent_member.agent_instance_id:
        return
    agent = ctx_db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
    if not agent or not sender.user_ref:
        return
    try:
        user_id = int(sender.user_ref)
    except (TypeError, ValueError):
        return
    ai_message = await create_pending_ai_message(
        ctx_db,
        group_id=int(group.id),
        sender_member_id=int(agent_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="personal_auto",
    )
    try:
        result = await invoke_agent(
            ctx_db,
            agent_id=int(agent.id),
            short_term_memory=_build_short_term_memory(ctx_db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "group_type": "personal",
                "group_id": int(group.id),
                "user_id": int(user_id),
                "input_text": str(content or ""),
            },
            trace_message_id=int(ai_message.id),
        )
        await emit_ai_reply(
            ctx_db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(agent_member.id),
            content=str(result.text or ""),
            trigger="personal_auto",
            ai_message_id=int(ai_message.id),
        )
    except Exception:
        await _mark_failed_reply(ai_message, reply_to_message_id=int(user_message.id), trigger="personal_auto", db=ctx_db)
        raise


async def _handle_project_manager(ctx_db: Session, group: Group, sender: Member, user_message: Message, content: str) -> None:
    manager_member = get_or_create_manager_member(ctx_db, group_id=int(group.id))
    ai_message = await create_pending_ai_message(
        ctx_db,
        group_id=int(group.id),
        sender_member_id=int(manager_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="manager_runtime",
    )
    try:
        result = await invoke_manager(
            ctx_db,
            group_id=int(group.id),
            short_term_memory=_build_short_term_memory(ctx_db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "purpose": "assistant",
                "input_text": str(content or ""),
                "group_type": "project",
                "group_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "sender_id": int(sender.id),
                "user_message_id": int(user_message.id),
            },
            trace_message_id=int(ai_message.id),
        )
        await emit_ai_reply(
            ctx_db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(manager_member.id),
            content=str(result.text or ""),
            trigger="manager_runtime",
            ai_message_id=int(ai_message.id),
        )
    except Exception:
        await _mark_failed_reply(ai_message, reply_to_message_id=int(user_message.id), trigger="manager_runtime", db=ctx_db)
        raise


async def _handle_project_mentions(ctx_db: Session, group: Group, sender: Member, user_message: Message, content: str, meta_json: str) -> None:
    mentioned_ids = _extract_agent_mentions(meta_json)
    await asyncio.gather(*[_handle_single_project_agent(ctx_db, group, sender, user_message, content, member_id) for member_id in mentioned_ids])


async def _handle_single_project_agent(
    ctx_db: Session,
    group: Group,
    sender: Member,
    user_message: Message,
    content: str,
    agent_member_id: int,
) -> None:
    agent_member = ctx_db.query(Member).filter(Member.id == int(agent_member_id)).first()
    if not agent_member or agent_member.kind != "agent" or int(agent_member.group_id) != int(group.id):
        return
    if not agent_member.agent_instance_id:
        return
    agent = ctx_db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
    if not agent:
        return
    try:
        await maybe_compress_project_memory(ctx_db, project_id=int(group.id), agent_id=int(agent.id))
    except Exception:
        pass
    ai_message = await create_pending_ai_message(
        ctx_db,
        group_id=int(group.id),
        sender_member_id=int(agent_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="mention",
    )
    try:
        result = await invoke_agent(
            ctx_db,
            agent_id=int(agent.id),
            short_term_memory=_build_short_term_memory(ctx_db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "group_type": "project",
                "group_id": int(group.id),
                "project_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "input_text": str(content or ""),
            },
            trace_message_id=int(ai_message.id),
        )
        await emit_ai_reply(
            ctx_db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(agent_member.id),
            content=str(result.text or ""),
            trigger="mention",
            ai_message_id=int(ai_message.id),
        )
    except Exception as exc:
        fallback_text = (
            f"@{agent_member.id} 执行失败：{str(exc)}\n"
            "我已经记录了这次错误，会继续尝试其他被 @ 的 agent。"
        )
        await emit_ai_reply(
            ctx_db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(agent_member.id),
            content=fallback_text,
            trigger="mention",
            status="failed",
            ai_message_id=int(ai_message.id),
        )


async def handle_group_ai_reply(request: GroupAIReplyRequest) -> None:
    ctx = _build_reply_context(
        request.db,
        group_id=int(request.group_id),
        sender_member_id=int(request.sender_member_id),
        user_message_id=int(request.user_message_id),
    )
    if ctx is None:
        return
    group, sender, user_message = ctx
    if sender.kind != "user" or request.message_type != "text":
        return
    try:
        if str(group.type) == "bootstrap":
            await _handle_bootstrap(request.db, group, sender, user_message, request.content, request.meta_json)
        elif str(group.type) == "personal":
            await _handle_personal(request.db, group, sender, user_message, request.content, request.meta_json)
        elif str(group.type) == "project":
            mentions = _extract_agent_mentions(request.meta_json)
            if not mentions:
                return
            cfg = request.db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group.id)).first()
            if cfg and int(cfg.enabled) == 1:
                manager_member = get_or_create_manager_member(request.db, group_id=int(group.id))
                if int(manager_member.id) in set(mentions):
                    await _handle_project_manager(request.db, group, sender, user_message, request.content)
                    return
            await _handle_project_mentions(request.db, group, sender, user_message, request.content, request.meta_json)
    except Exception as exc:
        await _broadcast_reply_failed(
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(sender.id),
            error=str(exc),
        )
        raise
