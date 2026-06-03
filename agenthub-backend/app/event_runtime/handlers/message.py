from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, status

from app.agent_runtime import invoke_agent
from app.bootstrap_runtime import invoke_bootstrap
from app.event_runtime.context import (
    EventDispatchRequest,
    build_reply_context,
    build_short_term_memory,
    broadcast_reply_failed,
    extract_agent_mentions,
    get_or_create_manager_member,
    mark_failed_reply,
    project_manager_enabled,
)
from app.event_runtime.types import MessageEventType
from app.agent_runtime.message_store import create_pending_ai_message
from app.manager_runtime import invoke_manager
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.event_runtime.reply import emit_ai_reply

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


async def handle_message_created(request: EventDispatchRequest, event: Any | None = None) -> None:
    _ = event
    ctx = build_reply_context(
        request.db,
        group_id=int(request.group_id),
        sender_member_id=int(request.sender_member_id),
        message_id=int(request.message_id),
    )
    if ctx is None:
        return
    group, sender, user_message = ctx
    if sender.kind != "user" or request.message_type != "text":
        return
    if str(group.type) == "bootstrap":
        if extract_agent_mentions(request.meta_json):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bootstrap group does not support mentions")
        await invoke_bootstrap(
            request.db,
            group_id=int(group.id),
            sender_member_id=int(sender.id),
            user_message_id=int(user_message.id),
            content=request.content,
            meta_json=request.meta_json,
            short_term_memory=build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "group_type": "bootstrap",
                "group_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "input_text": str(request.content or ""),
            },
        )
        return
    if str(group.type) == "personal":
        if extract_agent_mentions(request.meta_json):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Personal group does not support mentions")
        agent_member = (
            request.db.query(Member)
            .filter(Member.group_id == int(group.id), Member.kind == "agent")
            .order_by(Member.id.asc())
            .first()
        )
        if not agent_member or not agent_member.agent_instance_id:
            return
        agent = request.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
        if not agent or not sender.user_ref:
            return
        try:
            user_id = int(sender.user_ref)
        except (TypeError, ValueError):
            return
        ai_message = await create_pending_ai_message(
            request.db,
            group_id=int(group.id),
            sender_member_id=int(agent_member.id),
            reply_to_message_id=int(user_message.id),
            trigger="personal_auto",
        )
        try:
            result = await invoke_agent(
                request.db,
                agent_id=int(agent.id),
                short_term_memory=build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
                extra_context={
                    "group_type": "personal",
                    "group_id": int(group.id),
                    "user_id": int(user_id),
                    "input_text": str(request.content or ""),
                },
                trace_message_id=int(ai_message.id),
            )
            await emit_ai_reply(
                request.db,
                group_id=int(group.id),
                user_message_id=int(user_message.id),
                sender_member_id=int(agent_member.id),
                content=str(result.text or ""),
                trigger="personal_auto",
                ai_message_id=int(ai_message.id),
            )
        except Exception:
            await mark_failed_reply(ai_message, reply_to_message_id=int(user_message.id), trigger="personal_auto", db=request.db)
            raise
        return
    if str(group.type) == "project":
        mentioned_ids = extract_agent_mentions(request.meta_json)
        if not mentioned_ids:
            return
        if project_manager_enabled(request.db, group_id=int(group.id)):
            manager_member = get_or_create_manager_member(request.db, group_id=int(group.id))
            if int(manager_member.id) in set(mentioned_ids):
                await handle_project_manager(request, event)
                return
        await handle_project_mentions(request, event)


async def handle_project_manager(request: EventDispatchRequest, event: Any | None = None) -> None:
    _ = event
    group = request.db.query(Group).filter(Group.id == int(request.group_id)).first()
    sender = request.db.query(Member).filter(Member.id == int(request.sender_member_id)).first()
    user_message = request.db.query(Message).filter(Message.id == int(request.message_id)).first()
    if not group or not sender or not user_message:
        return
    manager_member = get_or_create_manager_member(request.db, group_id=int(group.id))
    ai_message = await create_pending_ai_message(
        request.db,
        group_id=int(group.id),
        sender_member_id=int(manager_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="manager_runtime",
    )
    try:
        result = await invoke_manager(
            request.db,
            group_id=int(group.id),
            short_term_memory=build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "purpose": "assistant",
                "input_text": str(request.content or ""),
                "group_type": "project",
                "group_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "sender_id": int(sender.id),
                "user_message_id": int(user_message.id),
            },
            trace_message_id=int(ai_message.id),
        )
        await emit_ai_reply(
            request.db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(manager_member.id),
            content=str(result.text or ""),
            trigger="manager_runtime",
            ai_message_id=int(ai_message.id),
        )
    except Exception:
        await mark_failed_reply(ai_message, reply_to_message_id=int(user_message.id), trigger="manager_runtime", db=request.db)
        raise


async def handle_project_mentions(request: EventDispatchRequest, event: Any | None = None) -> None:
    _ = event
    group = request.db.query(Group).filter(Group.id == int(request.group_id)).first()
    sender = request.db.query(Member).filter(Member.id == int(request.sender_member_id)).first()
    user_message = request.db.query(Message).filter(Message.id == int(request.message_id)).first()
    if not group or not sender or not user_message:
        return
    mentioned_ids = extract_agent_mentions(request.meta_json)
    await asyncio.gather(*[_handle_single_project_agent(request, member_id) for member_id in mentioned_ids])


async def _handle_single_project_agent(request: EventDispatchRequest, agent_member_id: int) -> None:
    group = request.db.query(Group).filter(Group.id == int(request.group_id)).first()
    sender = request.db.query(Member).filter(Member.id == int(request.sender_member_id)).first()
    user_message = request.db.query(Message).filter(Message.id == int(request.message_id)).first()
    if not group or not sender or not user_message:
        return
    agent_member = request.db.query(Member).filter(Member.id == int(agent_member_id)).first()
    if not agent_member or agent_member.kind != "agent" or int(agent_member.group_id) != int(group.id):
        return
    if not agent_member.agent_instance_id:
        return
    agent = request.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first()
    if not agent:
        return
    ai_message = await create_pending_ai_message(
        request.db,
        group_id=int(group.id),
        sender_member_id=int(agent_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="mention",
    )
    try:
        result = await invoke_agent(
            request.db,
            agent_id=int(agent.id),
            short_term_memory=build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "group_type": "project",
                "group_id": int(group.id),
                "project_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "input_text": str(request.content or ""),
            },
            trace_message_id=int(ai_message.id),
        )
        await emit_ai_reply(
            request.db,
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
            request.db,
            group_id=int(group.id),
            user_message_id=int(user_message.id),
            sender_member_id=int(agent_member.id),
            content=fallback_text,
            trigger="mention",
            status="failed",
            ai_message_id=int(ai_message.id),
        )


MESSAGE_EVENT_HANDLER_REGISTRY = {
    MessageEventType.InputOutput.MESSAGE_CREATED: handle_message_created,
    MessageEventType.InputOutput.MESSAGE_UPDATED: _handle_noop,
    MessageEventType.InputOutput.MESSAGE_ACCEPTED: _handle_noop,
    MessageEventType.InputOutput.REPLY_PLACEHOLDER_CREATED: _handle_noop,
    MessageEventType.InputOutput.REPLY_STARTED: _handle_noop,
    MessageEventType.InputOutput.REPLY_FINISHED: _handle_noop,
    MessageEventType.InputOutput.REPLY_FAILED: _handle_noop,
}
