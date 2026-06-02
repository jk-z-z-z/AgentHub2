from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.manager_runtime.assistant.decision import compose_reply_after_tool_calls, decide_manager_action
from app.manager_runtime.assistant.doc_update import run_doc_update_skill
from app.manager_runtime.assistant.planning import manager_tool_build_plan_with_llm, manager_tool_read_group_memory_context
from app.manager_runtime.managerbuilder._builder import build_complete_manager
from app.manager_runtime.schemas import ManagerInvokeResult
from app.manager_runtime.trace import ManagerRuntimeTrace
from app.manager_runtime.tool._executor import execute_manager_tool


def _trace_message_id(extra_context: dict[str, Any], explicit: int | None) -> int | None:
    if explicit is not None:
        return int(explicit)
    maybe = extra_context.get("trace_message_id")
    try:
        return int(maybe) if maybe not in (None, "") else None
    except (TypeError, ValueError):
        return None


async def _run_manager_tool(
    trace: ManagerRuntimeTrace,
    db: Session,
    *,
    group_id: int,
    tool_code: str,
    args: dict[str, Any],
) -> tuple[bool, Any, str | None]:
    payload_args = dict(args or {})
    trace.emit("manager.tool.call", {"tool_code": str(tool_code), "args": payload_args})
    result = await execute_manager_tool(db, tool_code=str(tool_code), args=payload_args, group_id=int(group_id))
    trace.emit(
        "manager.tool.result",
        {
            "tool_code": str(tool_code),
            "ok": bool(result.ok),
            "result": result.result,
            "error": result.error,
        },
    )
    return bool(result.ok), result.result, result.error


def _final_result(
    trace: ManagerRuntimeTrace,
    *,
    action: str,
    text: str,
    plan: dict[str, Any],
    built_group_type: str,
    purpose: str,
    group_id: int,
    system_prompt: str,
    decision: str | None = None,
) -> ManagerInvokeResult:
    trace.emit(
        "manager.final",
        {
            "action": action,
            "text_preview": str(text or "")[:800],
            "plan_node_count": len(plan.get("nodes") or []) if isinstance(plan, dict) else 0,
        },
    )
    meta: dict[str, Any] = {
        "purpose": purpose,
        "group_id": int(group_id),
        "group_type": built_group_type,
    }
    if decision is not None:
        meta["decision"] = decision
    return ManagerInvokeResult(
        text=str(text or ""),
        action=action,
        engine_type="manager_runtime",
        plan=plan,
        meta=meta,
        system_prompt_used=system_prompt,
    )


async def _run_plan_mode(
    trace: ManagerRuntimeTrace,
    *,
    db: Session,
    built_group_type: str,
    group_id: int,
    purpose: str,
    system_prompt: str,
    extra_context: dict[str, Any],
    built_runtime_context: dict[str, Any],
) -> ManagerInvokeResult:
    goal_text = str(extra_context.get("goal_text") or extra_context.get("input_text") or "").strip()
    trace.emit("manager.start", {"purpose": purpose, "group_id": int(group_id), "mode": "plan"})
    plan = await manager_tool_build_plan_with_llm(db=db, goal_text=goal_text, context=built_runtime_context)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    return _final_result(
        trace,
        action="plan",
        text=text,
        plan=plan,
        built_group_type=built_group_type,
        purpose=purpose,
        group_id=int(group_id),
        system_prompt=system_prompt,
    )


async def _run_assistant_mode(
    trace: ManagerRuntimeTrace,
    *,
    db: Session,
    built_group_type: str,
    group_id: int,
    purpose: str,
    system_prompt: str,
    extra_context: dict[str, Any],
    built_runtime_context: dict[str, Any],
) -> ManagerInvokeResult:
    goal_text = str(extra_context.get("input_text") or "").strip()
    trace.emit("manager.start", {"purpose": purpose, "group_id": int(group_id), "mode": "assistant"})

    memory_context = manager_tool_read_group_memory_context(db, group_id=int(group_id))
    pending_ok, pending_result, _ = await _run_manager_tool(
        trace,
        db,
        group_id=int(group_id),
        tool_code="manager.pending_state",
        args={"op": "load"},
    )
    pending_plan = (pending_result or {}).get("pending_plan") if pending_ok else None
    pending_clarify = (pending_result or {}).get("pending_clarify") if pending_ok else None
    short_term_preview = str(built_runtime_context.get("short_term_preview") or "")

    decision = await decide_manager_action(
        user_text=goal_text,
        pending_clarify=pending_clarify,
        pending_plan=pending_plan,
        memory_preview=str(memory_context.get("memory_preview") or ""),
        docs_preview=json.dumps(memory_context.get("docs_preview") or [], ensure_ascii=False),
        short_term_preview=short_term_preview,
    )
    trace.emit(
        "manager.decision",
        {
            "action": decision.action,
            "skills": decision.skills or [],
            "question_count": len(decision.questions or []),
            "tool_call_count": len(decision.tool_calls or []),
        },
    )

    tool_reply_text: str | None = None
    if "DOC_UPDATE" in set(decision.skills or []):
        skill_res = await run_doc_update_skill(
            user_text=goal_text,
            memory_preview=str(memory_context.get("memory_preview") or ""),
            docs_preview=json.dumps(memory_context.get("docs_preview") or [], ensure_ascii=False),
            short_term_preview=short_term_preview,
        )
        if skill_res.tool_calls:
            tool_results: list[dict[str, Any]] = []
            for tc in skill_res.tool_calls[:6]:
                tool_code = str(tc.get("tool_code") or "").strip()
                args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                ok, result, error = await _run_manager_tool(
                    trace,
                    db,
                    group_id=int(group_id),
                    tool_code=tool_code,
                    args=args,
                )
                tool_results.append({"tool_code": tool_code, "ok": ok, "result": result, "error": error})
            tool_reply_text = await compose_reply_after_tool_calls(
                user_text=goal_text,
                previous_reply_text=skill_res.reply_text,
                tool_results=tool_results,
            )
        else:
            tool_reply_text = skill_res.reply_text or "当前信息不足以沉淀文档。"

    if tool_reply_text is None and decision.tool_calls:
        tool_results = []
        for tc in decision.tool_calls[:6]:
            tool_code = str(tc.get("tool_code") or "").strip()
            args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
            ok, result, error = await _run_manager_tool(
                trace,
                db,
                group_id=int(group_id),
                tool_code=tool_code,
                args=args,
            )
            tool_results.append({"tool_code": tool_code, "ok": ok, "result": result, "error": error})
        tool_reply_text = await compose_reply_after_tool_calls(
            user_text=goal_text,
            previous_reply_text=decision.reply_text,
            tool_results=tool_results,
        )

    if decision.action == "APPLY_PLAN":
        if not pending_plan:
            text = tool_reply_text or decision.reply_text or "当前没有可执行的规划草案。请先让我生成DAG草案后再确认执行。"
            return _final_result(
                trace,
                action="assistant",
                text=text,
                plan={},
                built_group_type=built_group_type,
                purpose=purpose,
                group_id=int(group_id),
                system_prompt=system_prompt,
                decision=decision.action,
            )
        pending_creator = int(pending_plan.get("creator_member_id") or 0)
        if pending_creator and pending_creator != int(extra_context.get("sender_id") or extra_context.get("user_id") or 0):
            return _final_result(
                trace,
                action="assistant",
                text="该规划草案仅允许发起人确认。请让发起人回复“确认/执行”。",
                plan={},
                built_group_type=built_group_type,
                purpose=purpose,
                group_id=int(group_id),
                system_prompt=system_prompt,
            )
        plan = pending_plan.get("plan") or {}
        apply_ok, apply_result, apply_error = await _run_manager_tool(
            trace,
            db,
            group_id=int(group_id),
            tool_code="manager.apply_plan",
            args={
                "group_id": int(group_id),
                "actor_member_id": int(pending_creator or extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                "trigger_message_id": int(extra_context.get("user_message_id") or extra_context.get("message_id") or 0),
                "plan": plan,
            },
        )
        await _run_manager_tool(
            trace,
            db,
            group_id=int(group_id),
            tool_code="manager.pending_state",
            args={"op": "clear_plan"},
        )
        if tool_reply_text or decision.reply_text:
            text = tool_reply_text or decision.reply_text
        elif apply_ok:
            result = apply_result or {}
            text = f"已落库并开始分配执行。\nrun_id={result.get('run_id')} scheduled={result.get('scheduled_count')}"
        else:
            text = apply_error or "落库执行失败，请稍后重试。"
        return _final_result(
            trace,
            action="assistant",
            text=text,
            plan=plan if apply_ok else {},
            built_group_type=built_group_type,
            purpose=purpose,
            group_id=int(group_id),
            system_prompt=system_prompt,
            decision=decision.action,
        )

    if decision.action == "ASK_CLARIFY":
        questions = decision.questions or []
        if questions:
            await _run_manager_tool(
                trace,
                db,
                group_id=int(group_id),
                tool_code="manager.pending_state",
                args={
                    "op": "save_clarify",
                    "group_id": int(group_id),
                    "creator_member_id": int(extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                    "goal_text": goal_text,
                    "questions": questions,
                },
            )
        text = tool_reply_text or decision.reply_text or "我需要你补充一些关键信息后才能继续。"
        return _final_result(
            trace,
            action="assistant",
            text=text,
            plan={},
            built_group_type=built_group_type,
            purpose=purpose,
            group_id=int(group_id),
            system_prompt=system_prompt,
            decision=decision.action,
        )

    if decision.action == "DRAFT_PLAN":
        plan = decision.plan or {}
        if plan:
            await _run_manager_tool(
                trace,
                db,
                group_id=int(group_id),
                tool_code="manager.pending_state",
                args={
                    "op": "save_plan",
                    "group_id": int(group_id),
                    "creator_member_id": int(extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                    "plan": plan,
                },
            )
            await _run_manager_tool(
                trace,
                db,
                group_id=int(group_id),
                tool_code="manager.pending_state",
                args={"op": "clear_clarify", "group_id": int(group_id)},
            )
            text = tool_reply_text or decision.reply_text or json.dumps(plan, ensure_ascii=False, indent=2)
        else:
            text = tool_reply_text or decision.reply_text or "我已根据你的回答生成规划草案。"
        return _final_result(
            trace,
            action="assistant",
            text=text,
            plan=plan,
            built_group_type=built_group_type,
            purpose=purpose,
            group_id=int(group_id),
            system_prompt=system_prompt,
            decision=decision.action,
        )

    text = tool_reply_text or decision.reply_text or ""
    return _final_result(
        trace,
        action="assistant",
        text=text,
        plan={},
        built_group_type=built_group_type,
        purpose=purpose,
        group_id=int(group_id),
        system_prompt=system_prompt,
        decision=decision.action,
    )


async def invoke_manager(
    db: Session,
    *,
    group_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
    trace_message_id: int | None = None,
) -> ManagerInvokeResult:
    purpose = str(extra_context.get("purpose") or "chat").strip().lower()
    trace = ManagerRuntimeTrace(db=db, message_id=_trace_message_id(extra_context, trace_message_id))

    built = build_complete_manager(
        db,
        group_id=int(group_id),
        short_term_memory=short_term_memory,
        extra_context=extra_context,
    )

    if purpose == "plan":
        return await _run_plan_mode(
            trace,
            db=db,
            built_group_type=str(built.runtime_context.get("group_type") or "project"),
            group_id=int(group_id),
            purpose=purpose,
            system_prompt=built.system_prompt,
            extra_context=extra_context,
            built_runtime_context=built.runtime_context,
        )

    return await _run_assistant_mode(
        trace,
        db=db,
        built_group_type=str(built.runtime_context.get("group_type") or "project"),
        group_id=int(group_id),
        purpose=purpose,
        system_prompt=built.system_prompt,
        extra_context=extra_context,
        built_runtime_context=built.runtime_context,
    )
