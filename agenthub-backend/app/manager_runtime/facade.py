from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.manager_runtime.assistant.decision import compose_reply_after_tool_calls, decide_manager_action
from app.manager_runtime.assistant.doc_update import run_doc_update_skill
from app.manager_runtime.engine.factory import create_engine
from app.manager_runtime.managerbuilder._builder import build_complete_manager
from app.manager_runtime.assistant.planning import manager_tool_build_plan_with_llm
from app.manager_runtime.schemas import ManagerInvokeResult
from app.manager_runtime.tool._executor import execute_manager_tool
from app.manager_runtime.assistant.planning import manager_tool_read_group_memory_context


class _StrictManagerRunRequest:
    def __init__(
        self,
        *,
        group_id: int,
        input_text: str,
        purpose: str,
        system_prompt: str,
        runtime_context: dict[str, Any],
        short_term_memory: list[dict[str, Any]],
    ):
        self.group_id = group_id
        self.input_text = input_text
        self.purpose = purpose
        self.system_prompt = system_prompt
        self.runtime_context = runtime_context
        self.short_term_memory = short_term_memory


async def invoke_manager(
    db: Session,
    *,
    group_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
) -> ManagerInvokeResult:
    purpose = str(extra_context.get("purpose") or "chat").strip().lower()
    built = build_complete_manager(
        db,
        group_id=int(group_id),
        short_term_memory=short_term_memory,
        extra_context=extra_context,
    )
    engine = create_engine(built.engine_ctx.engine_type)
    req = _StrictManagerRunRequest(
        group_id=int(group_id),
        input_text=str(extra_context.get("goal_text") or extra_context.get("input_text") or ""),
        purpose=str(extra_context.get("purpose") or "chat"),
        system_prompt=built.system_prompt,
        runtime_context=built.runtime_context,
        short_term_memory=short_term_memory,
    )
    if purpose == "assistant":
        goal_text = str(extra_context.get("input_text") or "").strip()
        memory_context = manager_tool_read_group_memory_context(db, group_id=int(group_id))
        pending_res = await execute_manager_tool(db, tool_code="manager.pending_state", args={"op": "load"}, group_id=int(group_id))
        pending_plan = (pending_res.result or {}).get("pending_plan") if pending_res.ok else None
        pending_clarify = (pending_res.result or {}).get("pending_clarify") if pending_res.ok else None
        short_term_preview = str(built.runtime_context.get("short_term_preview") or "")
        decision = await decide_manager_action(
            user_text=goal_text,
            pending_clarify=pending_clarify,
            pending_plan=pending_plan,
            memory_preview=str(memory_context.get("memory_preview") or ""),
            docs_preview=json.dumps(memory_context.get("docs_preview") or [], ensure_ascii=False),
            short_term_preview=short_term_preview,
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
                tool_results: list[dict] = []
                for tc in skill_res.tool_calls[:6]:
                    tool_code = str(tc.get("tool_code") or "").strip()
                    args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                    res = await execute_manager_tool(db, tool_code=tool_code, args=args, group_id=int(group_id))
                    tool_results.append({"tool_code": tool_code, "ok": res.ok, "result": res.result, "error": res.error})
                tool_reply_text = await compose_reply_after_tool_calls(
                    user_text=goal_text,
                    previous_reply_text=skill_res.reply_text,
                    tool_results=tool_results,
                )
            else:
                tool_reply_text = skill_res.reply_text or "当前信息不足以沉淀文档。"

        if tool_reply_text is None and decision.tool_calls:
            tool_results: list[dict] = []
            for tc in decision.tool_calls[:6]:
                tool_code = str(tc.get("tool_code") or "").strip()
                args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                res = await execute_manager_tool(db, tool_code=tool_code, args=args, group_id=int(group_id))
                tool_results.append({"tool_code": tool_code, "ok": res.ok, "result": res.result, "error": res.error})
            tool_reply_text = await compose_reply_after_tool_calls(
                user_text=goal_text,
                previous_reply_text=decision.reply_text,
                tool_results=tool_results,
            )

        if decision.action == "APPLY_PLAN":
            if not pending_plan:
                text = tool_reply_text or decision.reply_text or "当前没有可执行的规划草案。请先让我生成DAG草案后再确认执行。"
                return ManagerInvokeResult(
                    text=text,
                    action="assistant",
                    engine_type="manager_runtime",
                    plan={},
                    meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project")},
                    system_prompt_used=built.system_prompt,
                )
            pending_creator = int(pending_plan.get("creator_member_id") or 0)
            if pending_creator and pending_creator != int(extra_context.get("sender_id") or extra_context.get("user_id") or 0):
                return ManagerInvokeResult(
                    text="该规划草案仅允许发起人确认。请让发起人回复“确认/执行”。",
                    action="assistant",
                    engine_type="manager_runtime",
                    plan={},
                    meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project")},
                    system_prompt_used=built.system_prompt,
                )
            plan = pending_plan.get("plan") or {}
            apply_res = await execute_manager_tool(
                db,
                tool_code="manager.apply_plan",
                args={
                    "group_id": int(group_id),
                    "actor_member_id": int(pending_creator or extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                    "trigger_message_id": int(extra_context.get("user_message_id") or extra_context.get("message_id") or 0),
                    "plan": plan,
                },
                group_id=int(group_id),
            )
            await execute_manager_tool(db, tool_code="manager.pending_state", args={"op": "clear_plan"}, group_id=int(group_id))
            if tool_reply_text or decision.reply_text:
                text = tool_reply_text or decision.reply_text
            elif apply_res.ok:
                result = apply_res.result or {}
                text = f"已落库并开始分配执行。\nrun_id={result.get('run_id')} scheduled={result.get('scheduled_count')}"
            else:
                text = apply_res.error or "落库执行失败，请稍后重试。"
            return ManagerInvokeResult(
                text=text,
                action="assistant",
                engine_type="manager_runtime",
                plan=plan if apply_res.ok else {},
                meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project"), "decision": decision.action},
                system_prompt_used=built.system_prompt,
            )

        if decision.action == "ASK_CLARIFY":
            questions = decision.questions or []
            if questions:
                await execute_manager_tool(
                    db,
                    tool_code="manager.pending_state",
                    args={
                        "op": "save_clarify",
                        "group_id": int(group_id),
                        "creator_member_id": int(extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                        "goal_text": goal_text,
                        "questions": questions,
                    },
                    group_id=int(group_id),
                )
            text = tool_reply_text or decision.reply_text or "我需要你补充一些关键信息后才能继续。"
            return ManagerInvokeResult(
                text=text,
                action="assistant",
                engine_type="manager_runtime",
                plan={},
                meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project"), "decision": decision.action},
                system_prompt_used=built.system_prompt,
            )

        if decision.action == "DRAFT_PLAN":
            plan = decision.plan or {}
            if plan:
                await execute_manager_tool(
                    db,
                    tool_code="manager.pending_state",
                    args={
                        "op": "save_plan",
                        "group_id": int(group_id),
                        "creator_member_id": int(extra_context.get("sender_id") or extra_context.get("user_id") or 0),
                        "plan": plan,
                    },
                    group_id=int(group_id),
                )
                await execute_manager_tool(db, tool_code="manager.pending_state", args={"op": "clear_clarify", "group_id": int(group_id)}, group_id=int(group_id))
                text = tool_reply_text or decision.reply_text or json.dumps(plan, ensure_ascii=False, indent=2)
            else:
                text = tool_reply_text or decision.reply_text or "我已根据你的回答生成规划草案。"
            return ManagerInvokeResult(
                text=text,
                action="assistant",
                engine_type="manager_runtime",
                plan=plan,
                meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project"), "decision": decision.action},
                system_prompt_used=built.system_prompt,
            )

        text = tool_reply_text or decision.reply_text or ""
        return ManagerInvokeResult(
            text=text,
            action="assistant",
            engine_type="manager_runtime",
            plan={},
            meta={"purpose": purpose, "group_id": int(group_id), "group_type": str(built.runtime_context.get("group_type") or "project"), "decision": decision.action},
            system_prompt_used=built.system_prompt,
        )

    text, meta = await engine.run(ctx=built.engine_ctx, req=req, tool_executor=None)
    plan = {}
    if isinstance(meta, dict):
        plan = meta.get("plan") if isinstance(meta.get("plan"), dict) else {}
    if str(extra_context.get("purpose") or "chat").strip().lower() == "plan" and not plan:
        plan = await manager_tool_build_plan_with_llm(
            db=db,
            goal_text=str(extra_context.get("goal_text") or extra_context.get("input_text") or ""),
            context=built.runtime_context,
        )
    return ManagerInvokeResult(
        text=str(text or ""),
        action=str(extra_context.get("purpose") or "chat"),
        engine_type=str(meta.get("engine") or "manager_internal_llm") if isinstance(meta, dict) else "manager_internal_llm",
        plan=plan,
        meta={
            "purpose": str(extra_context.get("purpose") or "chat"),
            "group_id": int(group_id),
            "group_type": str(built.runtime_context.get("group_type") or "project"),
            "engine_meta": meta if isinstance(meta, dict) else {},
        },
        system_prompt_used=built.system_prompt,
    )
