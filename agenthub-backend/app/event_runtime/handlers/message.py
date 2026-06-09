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
    extract_agent_mentions,
    extract_reply_to_message_id,
    get_or_create_manager_member,
    mark_failed_reply,
    project_manager_enabled,
)
from app.event_runtime.types import MessageEventType
from app.agent_runtime.message_store import create_pending_ai_message
from app.models.agent_instance import AgentInstance
from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.models.group_task_run import GroupTaskRun
from app.event_runtime.reply import emit_ai_reply
from app.manager_runtime.assistant.state_store import load_pending_clarify, load_pending_plan
EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


def _message_run_id_candidates(
    db: Any,
    *,
    current_message_id: int,
    meta_json: str,
) -> list[int]:
    candidates: list[int] = []
    seen: set[int] = set()

    def add_candidate(value: int | None) -> None:
        if value is None or int(value) in seen:
            return
        seen.add(int(value))
        candidates.append(int(value))

    add_candidate(int(current_message_id))
    reply_to_message_id = extract_reply_to_message_id(meta_json)
    add_candidate(reply_to_message_id)
    if reply_to_message_id is not None:
        reply_to_message = db.query(Message).filter(Message.id == int(reply_to_message_id)).first()
        if reply_to_message is not None:
            add_candidate(extract_reply_to_message_id(str(reply_to_message.metadata_json or "{}")))
    return candidates


def _resolve_manager_bound_run_id(
    db: Any,
    *,
    group_id: int,
    current_message_id: int,
    meta_json: str,
) -> int | None:
    candidate_ids = _message_run_id_candidates(
        db,
        current_message_id=int(current_message_id),
        meta_json=meta_json,
    )
    for candidate_id in candidate_ids:
        for payload in (
            load_pending_plan(group_id=int(group_id), trigger_message_id=int(candidate_id)),
            load_pending_clarify(group_id=int(group_id), trigger_message_id=int(candidate_id)),
        ):
            if not isinstance(payload, dict):
                continue
            try:
                run_id = int(payload.get("run_id"))
            except (TypeError, ValueError):
                run_id = None
            if run_id is not None:
                return run_id
    for candidate_id in candidate_ids:
        row = (
            db.query(GroupTaskRun)
            .filter(
                GroupTaskRun.group_id == int(group_id),
                GroupTaskRun.trigger_message_id == int(candidate_id),
            )
            .order_by(GroupTaskRun.id.desc())
            .first()
        )
        if row is not None:
            return int(row.id)
    return None


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
    from app.manager_runtime import invoke_manager

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
        effective_user_id = int(sender.user_ref) if sender.user_ref else None
        if effective_user_id is not None:
            short_term_memory = build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id))
            bound_run_id = _resolve_manager_bound_run_id(
                request.db,
                group_id=int(group.id),
                current_message_id=int(user_message.id),
                meta_json=str(request.meta_json or "{}"),
            )
            reply_to_message_id = extract_reply_to_message_id(str(request.meta_json or "{}"))
        result = await invoke_manager(
            request.db,
            group_id=int(group.id),
            short_term_memory=short_term_memory if effective_user_id is not None else build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "purpose": "assistant",
                "input_text": str(request.content or ""),
                "group_type": "project",
                "group_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "sender_id": int(sender.id),
                "user_message_id": int(user_message.id),
                "reply_to_message_id": int(reply_to_message_id) if "reply_to_message_id" in locals() and reply_to_message_id is not None else None,
                "source_message_id": int(reply_to_message_id) if "reply_to_message_id" in locals() and reply_to_message_id is not None else None,
                "run_id": int(bound_run_id) if "bound_run_id" in locals() and bound_run_id is not None else None,
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
            extra_metadata=result.meta,
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


def _has_task_runtime_context(payload: dict[str, Any]) -> bool:
    for key in ("run_id", "node_id", "task_id"):
        if payload.get(key) not in (None, ""):
            return True
    source_event_type = str(payload.get("source_event_type") or "")
    return source_event_type.startswith(("task.", "node.exec."))


async def handle_reply_finished(request: EventDispatchRequest, event: Any | None = None) -> None:
    from app.manager_runtime import invoke_manager

    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        return
    if str(payload.get("status") or "").lower() != "done":
        return
    if str(payload.get("trigger") or "") != "mention":
        return
    if not _has_task_runtime_context(payload):
        return
    group = request.db.query(Group).filter(Group.id == int(request.group_id)).first()
    sender = request.db.query(Member).filter(Member.id == int(request.sender_member_id)).first()
    user_message = request.db.query(Message).filter(Message.id == int(request.message_id)).first()
    if not group or not sender or not user_message:
        return
    if str(group.type) != "project" or sender.kind != "agent":
        return
    if not project_manager_enabled(request.db, group_id=int(group.id)):
        return
    agent_member = sender
    agent = request.db.query(AgentInstance).filter(AgentInstance.id == int(agent_member.agent_instance_id)).first() if agent_member.agent_instance_id else None
    if not agent:
        return
    manager_member = get_or_create_manager_member(request.db, group_id=int(group.id))
    ai_message = await create_pending_ai_message(
        request.db,
        group_id=int(group.id),
        sender_member_id=int(manager_member.id),
        reply_to_message_id=int(user_message.id),
        trigger="manager_runtime",
    )
    reply_text = str(payload.get("content") or request.content or "")
    try:
        result = await invoke_manager(
            request.db,
            group_id=int(group.id),
            short_term_memory=build_short_term_memory(request.db, group_id=int(group.id), exclude_message_id=int(user_message.id)),
            extra_context={
                "purpose": "evaluation",
                "goal_text": f"请评估刚才的 agent 回复，并在必要时更新任务状态或修改 DAG。\n\nagent_reply:\n{reply_text}",
                "group_type": "project",
                "group_id": int(group.id),
                "project_id": int(group.id),
                "user_id": int(sender.user_ref) if sender.user_ref else None,
                "sender_id": int(sender.id),
                "source_message_id": int(request.message_id),
                "source_reply_content": reply_text,
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
            extra_metadata=result.meta,
        )
    except Exception:
        await mark_failed_reply(ai_message, reply_to_message_id=int(user_message.id), trigger="manager_runtime", db=request.db)
        raise


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
            extra_metadata=result.meta,
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
    MessageEventType.InputOutput.REPLY_FINISHED: handle_reply_finished,
    MessageEventType.InputOutput.REPLY_FAILED: _handle_noop,
}
