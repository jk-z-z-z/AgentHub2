from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.services.group_ai_reply.context import ReplyContext
from app.services.group_ai_reply.agents.manager_agent import ManagerRoleAgent
from app.services.manager_planning_service import (
    manager_tool_read_group_memory_context,
)
from app.services.manager_assistant.types import ManagerAssistantResult
from app.services.manager_assistant.tools.pending_state_tool import PendingStateTool
from app.services.manager_assistant.tools.plan_apply_tool import PlanApplyTool
from app.services.manager_assistant.tools.project_md_tool import ProjectMdTool
from app.services.manager_assistant.skills.decision import (
    compose_reply_after_tool_calls,
    decide_manager_action,
)
from app.services.manager_assistant.skills.doc_update import run_doc_update_skill


class ManagerAssistantExecutor:
    """
    Group manager assistant (Master) conversation service.

    This executor owns:
    - chat vs clarify vs draft plan vs apply plan decisions (LLM-driven)
    - pending state transitions (pending_clarify / pending_plan)
    - calling orchestrator for apply+schedule

    The caller (strategy/engine) should only provide ReplyContext and a ManagerRoleAgent.
    """

    def __init__(self, *, agent: ManagerRoleAgent) -> None:
        self._agent = agent
        self._tools = {
            "manager.project_md": ProjectMdTool(),
        }

    async def handle(self, ctx: ReplyContext) -> ManagerAssistantResult:
        goal_text = str(ctx.content or "").strip()
        pending_tool = PendingStateTool()
        loaded = await pending_tool(op="load", group_id=int(ctx.group.id))
        pending_plan = (loaded.result or {}).get("pending_plan") if loaded.ok else None
        pending_clarify = (loaded.result or {}).get("pending_clarify") if loaded.ok else None
        context = manager_tool_read_group_memory_context(ctx.db, group_id=int(ctx.group.id))
        short_term_preview = self._build_short_term_preview(ctx)

        decision = await decide_manager_action(
            user_text=goal_text,
            pending_clarify=pending_clarify,
            pending_plan=pending_plan,
            memory_preview=str(context.get("memory_preview") or ""),
            docs_preview=json.dumps(context.get("docs_preview") or [], ensure_ascii=False),
            short_term_preview=short_term_preview,
        )

        # Skill routing (AI-driven). Skills may request tool calls.
        if "DOC_UPDATE" in set(decision.skills or []):
            skill_res = await run_doc_update_skill(
                user_text=goal_text,
                memory_preview=str(context.get("memory_preview") or ""),
                docs_preview=json.dumps(context.get("docs_preview") or [], ensure_ascii=False),
                short_term_preview=short_term_preview,
            )
            if skill_res.tool_calls:
                tool_results: list[dict] = []
                for tc in skill_res.tool_calls[:6]:
                    tool_code = str(tc.get("tool_code") or "").strip()
                    args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                    tool = self._tools.get(tool_code)
                    if not tool:
                        tool_results.append({"tool_code": tool_code, "ok": False, "error": "tool_not_allowed"})
                        continue
                    try:
                        res = await tool(group_id=int(ctx.group.id), **args)
                        tool_results.append({"tool_code": tool_code, "ok": res.ok, "result": res.result, "error": res.error})
                    except Exception as e:
                        tool_results.append({"tool_code": tool_code, "ok": False, "error": str(e)})

                reply_text = await compose_reply_after_tool_calls(
                    user_text=goal_text,
                    previous_reply_text=skill_res.reply_text,
                    tool_results=tool_results,
                )
                return ManagerAssistantResult(content=reply_text or skill_res.reply_text or "已执行文档更新。")
            return ManagerAssistantResult(content=skill_res.reply_text or "当前信息不足以沉淀文档。")

        # Optional tool calls (AI-driven). Execute before generating user-visible reply text.
        tool_reply_text: str | None = None
        if decision.tool_calls:
            tool_results: list[dict] = []
            for tc in decision.tool_calls[:6]:
                tool_code = str(tc.get("tool_code") or "").strip()
                args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                tool = self._tools.get(tool_code)
                if not tool:
                    tool_results.append({"tool_code": tool_code, "ok": False, "error": "tool_not_allowed"})
                    continue
                try:
                    res = await tool(group_id=int(ctx.group.id), **args)
                    tool_results.append({"tool_code": tool_code, "ok": res.ok, "result": res.result, "error": res.error})
                except Exception as e:  # keep user reply AI-authored; include error for model to explain
                    tool_results.append({"tool_code": tool_code, "ok": False, "error": str(e)})

            tool_reply_text = await compose_reply_after_tool_calls(
                user_text=goal_text,
                previous_reply_text=decision.reply_text,
                tool_results=tool_results,
            )

        if decision.action == "APPLY_PLAN":
            if not pending_plan:
                return ManagerAssistantResult(
                    content=tool_reply_text
                    or decision.reply_text
                    or "当前没有可执行的规划草案。请先让我生成DAG草案后再确认执行。"
                )
            # Enforce "only creator can confirm"
            pending_creator = int(pending_plan.get("creator_member_id") or 0)
            if pending_creator and pending_creator != int(ctx.sender.id):
                return ManagerAssistantResult(content="该规划草案仅允许发起人确认。请让发起人回复“确认/执行”。")

            plan = pending_plan.get("plan") or {}
            apply_tool = PlanApplyTool(db=ctx.db)
            applied = await apply_tool(
                group_id=int(ctx.group.id),
                actor_member_id=int(pending_creator or ctx.sender.id),
                trigger_message_id=int(ctx.user_message.id),
                plan=plan,
            )
            _ = await pending_tool(op="clear_plan", group_id=int(ctx.group.id))
            # Prefer model-written reply text; otherwise fallback to a concise system line.
            if tool_reply_text or decision.reply_text:
                return ManagerAssistantResult(content=tool_reply_text or decision.reply_text)
            if applied.ok:
                return ManagerAssistantResult(
                    content=f"已落库并开始分配执行。\nrun_id={applied.result.get('run_id')} scheduled={applied.result.get('scheduled_count')}"
                )
            return ManagerAssistantResult(content="落库执行失败，请稍后重试。")

        if decision.action == "ASK_CLARIFY":
            questions = decision.questions or []
            if questions:
                _ = await pending_tool(
                    op="save_clarify",
                    group_id=int(ctx.group.id),
                    creator_member_id=int(ctx.sender.id),
                    goal_text=goal_text,
                    questions=questions,
                )
            # Always return model-authored text to avoid program templates.
            return ManagerAssistantResult(content=tool_reply_text or decision.reply_text or "我需要你补充一些关键信息后才能继续。")

        if decision.action == "DRAFT_PLAN":
            # Prefer model-provided plan (pure AI-driven). Fallback to planner if missing.
            plan = decision.plan or {}
            if plan:
                _ = await pending_tool(op="save_plan", group_id=int(ctx.group.id), creator_member_id=int(ctx.sender.id), plan=plan)
                _ = await pending_tool(op="clear_clarify", group_id=int(ctx.group.id))
                return ManagerAssistantResult(content=tool_reply_text or decision.reply_text or json.dumps(plan, ensure_ascii=False, indent=2))
            # Fallback: build plan via manager planner (still LLM, but executor formats response).
            user_answers = goal_text if pending_clarify else None
            base_goal = str((pending_clarify or {}).get("goal_text") or goal_text)
            plan_text = await self._handle_draft(ctx, goal_text=base_goal, user_answers=user_answers)
            _ = await pending_tool(op="clear_clarify", group_id=int(ctx.group.id))
            return ManagerAssistantResult(content=plan_text)

        # CHAT
        return ManagerAssistantResult(
            content=tool_reply_text or decision.reply_text or (await self._agent.chat(ctx, text=goal_text))
        )

    def _build_short_term_preview(self, ctx: ReplyContext) -> str:
        from app.services.group_ai_reply.helpers import build_short_term_history_msgs

        short_term = build_short_term_history_msgs(
            ctx.db,
            group_id=int(ctx.group.id),
            exclude_message_id=int(ctx.user_message.id),
        )
        lines: list[str] = []
        for msg_item in short_term[-20:]:
            text = ""
            content_blocks = getattr(msg_item, "content", None)
            if isinstance(content_blocks, list) and content_blocks:
                first = content_blocks[0]
                text = str(first.get("text", "")) if isinstance(first, dict) else str(getattr(first, "text", "") or "")
            lines.append(f"{getattr(msg_item, 'name', 'user')}: {text}")
        return "\n".join(lines)

    async def _handle_draft(self, ctx: ReplyContext, *, goal_text: str, user_answers: str | None) -> str:
        context = manager_tool_read_group_memory_context(ctx.db, group_id=int(ctx.group.id))
        extra = {**context, "short_term_preview": self._build_short_term_preview(ctx)[:4000]}
        if user_answers:
            extra["clarify_answers"] = str(user_answers)[:4000]
        plan = await self._agent.build_plan(ctx, goal_text=goal_text, extra_context=extra)
        pending_tool = PendingStateTool()
        _ = await pending_tool(op="save_plan", group_id=int(ctx.group.id), creator_member_id=int(ctx.sender.id), plan=plan)
        return (
            "我已根据你的回答生成规划草案，请确认是否落库执行（回复：确认 / 同意 / 执行）。\n\n"
            "```json\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n"
            "```"
        )
