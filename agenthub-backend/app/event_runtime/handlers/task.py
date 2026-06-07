from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.agent_runtime import invoke_agent
from app.common.project_prompt import build_project_system_prompt
from app.event_runtime.context import EventDispatchRequest, build_short_term_memory
from app.event_runtime.facade import create_message_event
from app.event_runtime.types import MessageEventStatus, MessageEventType
from app.models.agent_instance import AgentInstance
from app.models.group_task_node import GroupTaskNode
from app.models.member import Member
from app.services.group_task_service import assign_node_to_agent, claim_node, get_node, mark_node_failed, requeue_node

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


def _derive_review_status(*, source_event_type: str, node_status: str) -> str:
    normalized_status = str(node_status or "").strip().lower()
    if normalized_status in {"completed", "failed"}:
        return normalized_status
    if normalized_status == "pending":
        return "requeued"
    if str(source_event_type) == MessageEventType.Task.TASK_FAILED:
        return "failed"
    return "completed"


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
    return {
        "node_id": int(node.id),
        "run_id": int(node.run_id),
        "node_key": str(node.node_key),
        "status": "completed",
        "output_summary": str(result.text or "节点执行完成"),
    }


async def handle_node_exec_started(request: EventDispatchRequest, event: Any | None = None) -> None:
    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    try:
        result = await execute_node_task(
            request,
            node_id=int(node_id),
            member_id=int(member_id),
            trace_message_id=int(request.message_id),
        )
        node = get_node(request.db, node_id=int(node_id))
        if node:
            create_message_event(
                request.db,
                message_id=int(request.message_id),
                event_type=MessageEventType.Task.TASK_COMPLETED,
                payload={
                    "node_id": int(node.id),
                    "run_id": int(node.run_id),
                    "node_key": str(node.node_key),
                    "member_id": int(member_id),
                    "status": "completed",
                    "output_summary": str(result.get("output_summary") or ""),
                    "source_event_type": MessageEventType.Task.NODE_EXEC_STARTED,
                },
                run_id=int(node.run_id),
                status=MessageEventStatus.PENDING,
            )
    except Exception as exc:
        if request.message_id is not None:
            try:
                create_message_event(
                    request.db,
                    message_id=int(request.message_id),
                    event_type=MessageEventType.Task.TASK_FAILED,
                    payload={
                        "node_id": int(node_id),
                        "run_id": int(node.run_id) if "node" in locals() and node else payload.get("run_id"),
                        "member_id": int(member_id),
                        "status": "failed",
                        "error": str(exc),
                        "source_event_type": MessageEventType.Task.NODE_EXEC_STARTED,
                    },
                    run_id=int(node.run_id) if "node" in locals() and node else None,
                    status=MessageEventStatus.PENDING,
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
    from app.manager_runtime import invoke_manager

    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    member_id = payload.get("member_id")
    if node_id is None or member_id is None:
        return
    node = get_node(request.db, node_id=int(node_id))
    if not node:
        return
    source_event_type = str(event.event_type) if event is not None else MessageEventType.Task.TASK_COMPLETED
    review_status = _derive_review_status(
        source_event_type=source_event_type,
        node_status=str(node.status),
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
    result = await invoke_manager(
        request.db,
        group_id=int(node.group_id),
        short_term_memory=build_short_term_memory(
            request.db,
            group_id=int(node.group_id),
            exclude_message_id=int(request.message_id),
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
            "node_status": str(final_node.status),
            "node_output_summary": output_summary,
            "review_status": review_status,
            "goal_text": _build_review_prompt(
                node=final_node,
                member_id=int(member_id),
                status=review_status,
                output_summary=output_summary,
                error=error_text,
                source_message_id=int(request.message_id),
            ),
            "input_text": _build_review_prompt(
                node=final_node,
                member_id=int(member_id),
                status=review_status,
                output_summary=output_summary,
                error=error_text,
                source_message_id=int(request.message_id),
            ),
        },
        trace_message_id=int(request.message_id),
    )
    create_message_event(
        request.db,
        message_id=int(request.message_id),
        event_type=MessageEventType.Task.TASK_REVIEWED,
        payload={
            "node_id": int(node.id),
            "run_id": int(node.run_id),
            "node_key": str(node.node_key),
            "member_id": int(member_id),
            "review_status": review_status,
            "source_event_type": source_event_type,
            "review_text": str(getattr(result, "text", "") or ""),
        },
        run_id=int(node.run_id),
        status=MessageEventStatus.PENDING,
    )


async def handle_task_failed(request: EventDispatchRequest, event: Any | None = None) -> None:
    from app.manager_runtime import invoke_manager

    payload = _payload_as_dict(event)
    node_id = payload.get("node_id")
    if node_id is None:
        return
    node = get_node(request.db, node_id=int(node_id))
    if not node:
        return
    source_event_type = str(event.event_type) if event is not None else MessageEventType.Task.TASK_FAILED
    review_status = _derive_review_status(
        source_event_type=source_event_type,
        node_status=str(node.status),
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
    result = await invoke_manager(
        request.db,
        group_id=int(node.group_id),
        short_term_memory=build_short_term_memory(
            request.db,
            group_id=int(node.group_id),
            exclude_message_id=int(request.message_id),
        ),
        extra_context={
            "purpose": "node_review",
            "group_type": "project",
            "group_id": int(node.group_id),
            "project_id": int(node.group_id),
            "run_id": int(node.run_id),
            "node_id": int(node.id),
            "node_key": str(node.node_key),
            "member_id": int(payload.get("member_id") or 0),
            "source_event_type": source_event_type,
            "source_message_id": int(request.message_id),
            "node_status": str(final_node.status),
            "node_error": error_text,
            "review_status": review_status,
            "goal_text": _build_review_prompt(
                node=final_node,
                member_id=int(payload.get("member_id") or 0),
                status=review_status,
                output_summary=output_summary,
                error=error_text,
                source_message_id=int(request.message_id),
            ),
            "input_text": _build_review_prompt(
                node=final_node,
                member_id=int(payload.get("member_id") or 0),
                status=review_status,
                output_summary=output_summary,
                error=error_text,
                source_message_id=int(request.message_id),
            ),
        },
        trace_message_id=int(request.message_id),
    )
    create_message_event(
        request.db,
        message_id=int(request.message_id),
        event_type=MessageEventType.Task.TASK_REVIEWED,
        payload={
            "node_id": int(node.id),
            "run_id": int(node.run_id),
            "node_key": str(node.node_key),
            "member_id": int(payload.get("member_id") or 0),
            "review_status": review_status,
            "source_event_type": source_event_type,
            "review_text": str(getattr(result, "text", "") or ""),
        },
        run_id=int(node.run_id),
        status=MessageEventStatus.PENDING,
    )


async def handle_task_reviewed(_request: EventDispatchRequest, _event: Any | None = None) -> None:
    return


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
