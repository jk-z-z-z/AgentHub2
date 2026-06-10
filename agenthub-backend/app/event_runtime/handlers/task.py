from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.agent_runtime import invoke_agent
from app.agent_runtime.message_store import create_pending_ai_message, dispatch_message_event_for_message
from app.common.project_prompt import build_project_system_prompt
from app.event_runtime.context import EventDispatchRequest, build_short_term_memory, get_or_create_manager_member, mark_failed_reply
from app.event_runtime.facade import create_message_event, list_message_events
from app.event_runtime.reply import emit_ai_reply
from app.event_runtime.types import MessageEventStatus, MessageEventType
from app.models.agent_instance import AgentInstance
from app.models.group_task_node import GroupTaskNode
from app.models.member import Member
from app.services.group_task_service import assign_node_to_agent, claim_node, get_node, mark_node_failed, requeue_node, review_node

EventHandler = Callable[[EventDispatchRequest, Any | None], Awaitable[None]]


async def _handle_noop(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


def _build_execution_prompt(*, node_key: str, title: str, detail: str) -> str:
    return (
        "你负责执行任务节点。\n"
        f"node_key={node_key}\n"
        f"title={title}\n"
        f"detail={detail}\n"
        "请输出结果 JSON，包含 summary、status、deliverables、evidence、confidence、issues、suggested_ops。"
    )


def _build_agent_execution_reply_text(result: dict[str, Any]) -> str:
    payload = result.get("result_payload")
    if isinstance(payload, dict):
        parsed_result = payload.get("parsed_result")
        if isinstance(parsed_result, dict):
            for key in ("summary", "output_summary", "message"):
                value = str(parsed_result.get(key) or "").strip()
                if value:
                    return value
        summary = str(payload.get("summary") or "").strip()
        if summary:
            return summary
    summary = str(result.get("output_summary") or "").strip()
    if summary:
        return summary
    return "节点执行完成"


def _schedule_message_dispatch(
    *,
    group_id: int,
    sender_member_id: int,
    message_id: int,
    message_type: str,
    content: str,
    meta_json: str,
) -> None:
    try:
        import asyncio

        asyncio.create_task(
            dispatch_message_event_for_message(
                group_id=int(group_id),
                sender_member_id=int(sender_member_id),
                message_id=int(message_id),
                message_type=str(message_type),
                content=str(content),
                meta_json=str(meta_json),
            )
        )
    except RuntimeError:
        return


def _payload_as_dict(event: Any | None) -> dict[str, Any]:
    payload = getattr(event, "payload", None) if event is not None else None
    return payload if isinstance(payload, dict) else {}


def _resolve_node_agent(db: Any, *, node_id: int, member_id: int) -> tuple[Any | None, Any | None, Any | None]:
    node = get_node(db, node_id=int(node_id))
    if not node:
        return None, None, None
    member = db.query(Member).filter(Member.id == int(member_id)).first()
    if not member or not member.agent_instance_id:
        return node, member, None
    agent = db.query(AgentInstance).filter(AgentInstance.id == int(member.agent_instance_id)).first()
    return node, member, agent


def _build_review_prompt(
    *,
    node: GroupTaskNode,
    member_id: int,
    status: str,
    output_summary: str,
    error: str | None = None,
    source_message_id: int | None = None,
) -> str:
    payload = {
        "node_id": int(node.id),
        "node_key": str(node.node_key),
        "group_id": int(node.group_id),
        "run_id": int(node.run_id),
        "member_id": int(member_id),
        "status": str(status),
        "output_summary": str(output_summary or ""),
        "error": str(error or ""),
        "source_message_id": int(source_message_id) if source_message_id is not None else None,
    }
    return (
        "你是管家 agent，需要复核子 agent 的节点执行结果。\n"
        "你的目标是：\n"
        "1. 判断该节点是否真正完成；\n"
        "2. 必要时修正节点状态、补充输出总结、更新 DAG；\n"
        "3. 如果发现执行结果不足或失败，继续安排后续动作。\n"
        "下面是本次执行结果：\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "请直接执行你需要的工具操作，并在最后给出简短结论。"
    )


async def _run_manager_review_flow(
    request: EventDispatchRequest,
    *,
    node: GroupTaskNode,
    member_id: int,
    source_event_type: str,
    review_status: str,
    output_summary: str,
    error_text: str,
) -> None:
    from app.manager_runtime import invoke_manager

    manager_member = get_or_create_manager_member(request.db, group_id=int(node.group_id))
    manager_message = await create_pending_ai_message(
        request.db,
        group_id=int(node.group_id),
        sender_member_id=int(manager_member.id),
        reply_to_message_id=int(request.message_id),
        trigger="manager_runtime",
    )
    review_prompt = _build_review_prompt(
        node=node,
        member_id=int(member_id),
        status=review_status,
        output_summary=output_summary,
        error=error_text,
        source_message_id=int(request.message_id),
    )
    result = await invoke_manager(
        request.db,
        group_id=int(node.group_id),
        short_term_memory=build_short_term_memory(
            request.db,
            group_id=int(node.group_id),
            exclude_message_id=int(manager_message.id),
        ),
        extra_context={
            "purpose": "node_review",
            "group_type": "project",
            "group_id": int(node.group_id),
            "project_id": int(node.group_id),
            "run_id": int(node.run_id),
            "node_id": int(node.id),
            "node_key": str(node.node_key),
            "member_id": int(member_id),
            "source_event_type": source_event_type,
            "source_message_id": int(request.message_id),
            "source_reply_message_id": int(request.message_id),
            "node_status": str(node.status),
            "node_output_summary": output_summary,
            "node_error": error_text,
            "review_status": review_status,
            "goal_text": review_prompt,
            "input_text": review_prompt,
        },
        trace_message_id=int(manager_message.id),
    )
    result_meta = result.meta if isinstance(getattr(result, "meta", None), dict) else {}
    create_message_event(
        request.db,
        message_id=int(manager_message.id),
        event_type=MessageEventType.Task.TASK_REVIEWED,
        payload={
            "node_id": int(node.id),
            "run_id": int(node.run_id),
            "node_key": str(node.node_key),
            "member_id": int(member_id),
            "review_status": review_status,
            "manager_review_status": str(result_meta.get("manager_review_status") or ""),
            "source_event_type": source_event_type,
            "source_message_id": int(request.message_id),
            "review_text": str(getattr(result, "text", "") or ""),
            "review_meta": result_meta,
        },
        run_id=int(node.run_id),
        status=MessageEventStatus.PENDING,
    )
    await emit_ai_reply(
        request.db,
        group_id=int(node.group_id),
        user_message_id=int(request.message_id),
        sender_member_id=int(manager_member.id),
        content=str(getattr(result, "text", "") or ""),
        trigger="manager_runtime",
        ai_message_id=int(manager_message.id),
        extra_metadata=result_meta,
        auto_dispatch_on_done=True,
    )


def _derive_review_status(*, source_event_type: str, node_status: str) -> str:
    normalized_status = str(node_status or "").strip().lower()
    if normalized_status in {"completed", "failed"}:
        return normalized_status
    if normalized_status == "pending":
        return "requeued"
    if str(source_event_type) == MessageEventType.Task.TASK_FAILED:
        return "failed"
    return "completed"


def _derive_manager_review_status(*, node: GroupTaskNode, payload: dict[str, Any]) -> str | None:
    explicit_status = str(payload.get("manager_review_status") or payload.get("review_status") or "").strip().lower()
    if explicit_status in {"approved", "rework"}:
        return explicit_status
    normalized_node_status = str(node.status or "").strip().lower()
    if explicit_status == "completed" and normalized_node_status == "completed":
        return "approved"
    if explicit_status in {"failed", "requeued"}:
        return "rework"
    if normalized_node_status == "completed":
        return "approved"
    if normalized_node_status in {"blocked", "failed", "pending"}:
        return "rework"
    return None


def _parse_node_result_text(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {"summary": text}
    return payload if isinstance(payload, dict) else {"summary": text}


def _collect_execution_artifacts(db: Any, *, message_id: int) -> dict[str, Any]:
    changed_files: list[str] = []
    validation_tools: list[str] = []
    preview_urls: list[str] = []
    deploy_urls: list[str] = []
    successful_tools: list[str] = []

    for event in list_message_events(db, message_id=int(message_id)):
        if str(event.event_type) != MessageEventType.Execution.TOOL_RESULT:
            continue
        payload = event.payload
        if not isinstance(payload, dict):
            continue
        tool_code = str(payload.get("tool_code") or "").strip()
        if not tool_code or payload.get("error") not in (None, ""):
            continue
        result = payload.get("result")
        successful_tools.append(tool_code)
        if tool_code == "project_code_write" and isinstance(result, dict):
            path = str(result.get("path") or "").strip()
            if path:
                changed_files.append(path)
        elif tool_code == "project_command_run":
            validation_tools.append(tool_code)
        elif tool_code == "project_preview_run" and isinstance(result, dict):
            validation_tools.append(tool_code)
            url = str(result.get("url") or "").strip()
            if url:
                preview_urls.append(url)
        elif tool_code == "project_deploy_run" and isinstance(result, dict):
            validation_tools.append(tool_code)
            url = str(result.get("url") or "").strip()
            if url:
                deploy_urls.append(url)

    return {
        "changed_files": list(dict.fromkeys(changed_files)),
        "validation_tools": list(dict.fromkeys(validation_tools)),
        "preview_urls": list(dict.fromkeys(preview_urls)),
        "deploy_urls": list(dict.fromkeys(deploy_urls)),
        "successful_tools": list(dict.fromkeys(successful_tools)),
        "has_substantive_artifact": bool(changed_files or validation_tools or preview_urls or deploy_urls),
    }


def _apply_review_status(
    db: Any,
    *,
    node: GroupTaskNode,
    member_id: int,
    review_status: str,
    output_summary: str,
    error: str,
) -> GroupTaskNode:
    current_status = str(node.status or "").strip().lower()
    target_status = str(review_status or "").strip().lower()
    if target_status == "completed":
        if current_status != "completed":
            return invoke_completion(db, node=node, member_id=member_id, output_summary=output_summary)
        return node
    if target_status == "failed":
        if current_status != "failed":
            return mark_node_failed(db, node_id=int(node.id), error=error)
        return node
    if target_status == "requeued":
        if current_status != "pending":
            return requeue_node(db, node_id=int(node.id), reason=error)
        return node
    return node


def invoke_completion(db: Any, *, node: GroupTaskNode, member_id: int, output_summary: str) -> GroupTaskNode:
    from app.services.group_task_service import complete_node

    return complete_node(
        db,
        node_id=int(node.id),
        member_id=int(member_id),
        output_summary=str(output_summary or ""),
    )


async def execute_node_task(
    request: EventDispatchRequest,
    *,
    node_id: int,
    member_id: int,
    trace_message_id: int | None = None,
) -> dict[str, Any]:
    node, member, agent = _resolve_node_agent(request.db, node_id=int(node_id), member_id=int(member_id))
    if not node:
        raise ValueError("node_not_found")
    if not member:
        raise ValueError("agent_member_not_found")
    if not agent:
        raise ValueError("agent_not_found")

    system_prompt = build_project_system_prompt(agent_id=int(agent.id), project_id=int(node.group_id))
    prompt = _build_execution_prompt(node_key=str(node.node_key), title=str(node.title), detail=str(node.detail))
    result = await invoke_agent(
        request.db,
        agent_id=int(agent.id),
        short_term_memory=build_short_term_memory(
            request.db,
            group_id=int(node.group_id),
            exclude_message_id=int(request.message_id),
        ),
        extra_context={
            "group_id": int(node.group_id),
            "run_id": int(node.run_id),
            "node_id": int(node.id),
            "input_text": prompt,
        },
        system_prompt=system_prompt,
        trace_message_id=int(trace_message_id) if trace_message_id is not None else None,
    )
    parsed_result = _parse_node_result_text(str(result.text or ""))
    artifact_summary = _collect_execution_artifacts(request.db, message_id=int(request.message_id))
    summary = str(
        parsed_result.get("summary")
        or parsed_result.get("output_summary")
        or parsed_result.get("message")
        or result.text
        or ""
    ).strip()
    if artifact_summary["has_substantive_artifact"]:
        final_status = "completed"
        final_summary = summary or "节点执行完成"
        error_text = ""
    else:
        final_status = "pending"
        final_summary = summary or "未检测到真实代码写入或验证产物，节点未完成。"
        error_text = "未检测到真实代码写入或验证产物，不能将节点标记为完成。"
    return {
        "node_id": int(node.id),
        "run_id": int(node.run_id),
        "node_key": str(node.node_key),
        "status": final_status,
        "output_summary": final_summary,
        "error": error_text,
        "result_payload": {
            "summary": final_summary,
            "status": final_status,
            "agent_output": str(result.text or ""),
            "parsed_result": parsed_result,
            "artifacts": artifact_summary,
        },
    }


async def handle_node_exec_started(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    node = get_node(request.db, node_id=int(node_id))
    member = request.db.query(Member).filter(Member.id == int(member_id)).first()
    if not node or not member:
        return
    trigger = f"node_execute:{int(node.id)}"
    ai_message = await create_pending_ai_message(
        request.db,
        group_id=int(node.group_id),
        sender_member_id=int(member.id),
        reply_to_message_id=int(request.message_id),
        trigger=trigger,
    )
    try:
        result = await execute_node_task(
            request,
            node_id=int(node_id),
            member_id=int(member_id),
            trace_message_id=int(ai_message.id),
        )
        node = get_node(request.db, node_id=int(node_id))
        if node:
            create_message_event(
                request.db,
                message_id=int(ai_message.id),
                event_type=(
                    MessageEventType.Task.TASK_FAILED
                    if str(result.get("status") or "").strip().lower() == "failed"
                    else MessageEventType.Task.TASK_COMPLETED
                ),
                payload={
                    "node_id": int(node.id),
                    "run_id": int(node.run_id),
                    "node_key": str(node.node_key),
                    "member_id": int(member_id),
                    "status": str(result.get("status") or "completed"),
                    "output_summary": str(result.get("output_summary") or ""),
                    "error": str(result.get("error") or ""),
                    "source_message_id": int(request.message_id),
                    "agent_message_id": int(ai_message.id),
                    "result_payload": result.get("result_payload") if isinstance(result.get("result_payload"), dict) else {},
                    "source_event_type": MessageEventType.Task.NODE_EXEC_STARTED,
                },
                run_id=int(node.run_id),
                status=MessageEventStatus.PENDING,
            )
        await emit_ai_reply(
            request.db,
            group_id=int(node.group_id),
            user_message_id=int(request.message_id),
            sender_member_id=int(member.id),
            content=_build_agent_execution_reply_text(result),
            trigger=trigger,
            ai_message_id=int(ai_message.id),
            extra_metadata={
                "node_execution": {
                    "node_id": int(node.id),
                    "run_id": int(node.run_id),
                    "node_key": str(node.node_key),
                    "member_id": int(member.id),
                    "status": str(result.get("status") or ""),
                    "output_summary": str(result.get("output_summary") or ""),
                    "error": str(result.get("error") or ""),
                }
            },
            auto_dispatch_on_done=True,
        )
    except Exception as exc:
        try:
            create_message_event(
                request.db,
                message_id=int(ai_message.id),
                event_type=MessageEventType.Task.TASK_FAILED,
                payload={
                    "node_id": int(node_id),
                    "run_id": int(node.run_id) if node else payload.get("run_id"),
                    "member_id": int(member_id),
                    "status": "failed",
                    "error": str(exc),
                    "source_message_id": int(request.message_id),
                    "agent_message_id": int(ai_message.id),
                    "source_event_type": MessageEventType.Task.NODE_EXEC_STARTED,
                },
                run_id=int(node.run_id) if node else None,
                status=MessageEventStatus.PENDING,
            )
        except Exception:
            pass
        try:
            await mark_failed_reply(
                ai_message,
                reply_to_message_id=int(request.message_id),
                trigger=trigger,
                db=request.db,
            )
            _schedule_message_dispatch(
                group_id=int(node.group_id) if node else int(request.group_id),
                sender_member_id=int(member.id),
                message_id=int(ai_message.id),
                message_type="ai",
                content="AI 回复失败，请稍后重试。",
                meta_json=f'{{"reply_to":"{int(request.message_id)}","trigger":"{trigger}","status":"failed"}}',
            )
        except Exception:
            pass
        return


async def handle_node_exec_finished(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    await handle_task_completed(_request, _event)


async def handle_task_assigned(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    assign_node_to_agent(request.db, node_id=int(node_id), member_id=int(member_id))


async def handle_task_claimed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = getattr(event, "payload", None) if event is not None else None
    if not isinstance(payload, dict):
        payload = {}
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    claim_node(request.db, node_id=int(node_id), member_id=int(member_id))


async def handle_task_completed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    node = get_node(request.db, node_id=int(node_id))
    if not node:
        return
    source_event_type = str(event.event_type) if event is not None else MessageEventType.Task.TASK_COMPLETED
    observed_status = str(payload.get("status") or node.status)
    review_status = _derive_review_status(
        source_event_type=source_event_type,
        node_status=observed_status,
    )
    output_summary = str(payload.get("output_summary") or "")
    error_text = str(payload.get("error") or "")
    final_node = _apply_review_status(
        request.db,
        node=node,
        member_id=int(member_id),
        review_status=review_status,
        output_summary=output_summary,
        error=error_text,
    )
    await _run_manager_review_flow(
        request,
        node=final_node,
        member_id=int(member_id),
        source_event_type=source_event_type,
        review_status=review_status,
        output_summary=output_summary,
        error_text=error_text,
    )


async def handle_task_failed(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    if node_id is None:
        return
    node = get_node(request.db, node_id=int(node_id))
    if not node:
        return
    source_event_type = str(event.event_type) if event is not None else MessageEventType.Task.TASK_FAILED
    observed_status = str(payload.get("status") or node.status)
    review_status = _derive_review_status(
        source_event_type=source_event_type,
        node_status=observed_status,
    )
    output_summary = str(payload.get("output_summary") or "")
    error_text = str(payload.get("error") or "")
    final_node = _apply_review_status(
        request.db,
        node=node,
        member_id=int(payload.get("member_id") or 0),
        review_status=review_status,
        output_summary=output_summary,
        error=error_text,
    )
    await _run_manager_review_flow(
        request,
        node=final_node,
        member_id=int(payload.get("member_id") or 0),
        source_event_type=source_event_type,
        review_status=review_status,
        output_summary=output_summary,
        error_text=error_text,
    )


async def handle_task_reviewed(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    payload = _payload_as_dict(_event)
    node_id = payload.get("node_id")
    if node_id is None:
        return
    node = get_node(_request.db, node_id=int(node_id))
    if not node:
        return
    manager_review_status = _derive_manager_review_status(node=node, payload=payload)
    if manager_review_status is None:
        return
    manager_member = get_or_create_manager_member(_request.db, group_id=int(node.group_id))
    review_note = str(payload.get("review_text") or node.output_summary or node.error or "").strip()
    review_node(
        _request.db,
        node_id=int(node.id),
        reviewer_member_id=int(manager_member.id),
        manager_review_status=manager_review_status,
        note=review_note,
    )


TASK_EVENT_HANDLER_REGISTRY = {
    MessageEventType.Task.TASK_CREATED: _handle_noop,
    MessageEventType.Task.TASK_ASSIGNED: handle_task_assigned,
    MessageEventType.Task.TASK_CLAIMED: handle_task_claimed,
    MessageEventType.Task.TASK_COMPLETED: handle_task_completed,
    MessageEventType.Task.TASK_FAILED: handle_task_failed,
    MessageEventType.Task.TASK_REVIEWED: handle_task_reviewed,
    MessageEventType.Task.TASK_REQUEUED: _handle_noop,
    MessageEventType.Task.NODE_EXEC_STARTED: handle_node_exec_started,
    MessageEventType.Task.NODE_EXEC_FINISHED: handle_node_exec_finished,
}
