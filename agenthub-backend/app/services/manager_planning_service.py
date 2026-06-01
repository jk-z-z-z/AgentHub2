from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.group_task_run import GroupTaskRun
from app.agent_runtime.internal_llm import internal_llm_chat

# NOTE: Manager (group capability) is fixed to internal LLM path.
# It must NOT be delegated to ACP / external runners.
from app.services.group_task.node_service import create_group_task_run, list_group_task_runs, update_group_task_dag
from app.services.storage_paths import project_dir


def manager_tool_read_group_memory_context(db: Session, *, group_id: int) -> dict:
    root = project_dir(int(group_id))
    memory = root / "MEMORY.md"
    memory_text = memory.read_text(encoding="utf-8") if memory.exists() else ""
    docs_dir = root / "knowledge"
    docs_preview: list[dict] = []
    if docs_dir.exists() and docs_dir.is_dir():
        for p in sorted(docs_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            preview = ""
            try:
                preview = p.read_text(encoding="utf-8")[:200]
            except Exception:
                preview = ""
            docs_preview.append({"path": rel, "preview": preview})
            if len(docs_preview) >= 8:
                break
    return {
        "group_id": int(group_id),
        "memory_file": memory.as_posix(),
        "memory_exists": memory.exists(),
        "memory_preview": memory_text[:1200],
        "docs_preview": docs_preview,
    }


def manager_tool_build_plan(*, goal_text: str, context: dict | None = None) -> dict:
    goal = str(goal_text or "").strip() or "请补充目标交付物定义"
    nodes = [
        {"node_key": "N1", "title": "需求澄清", "detail": "明确交付物、范围、验收标准", "role_required": "manager", "deps": []},
        {"node_key": "N2", "title": "方案设计", "detail": "输出技术方案、接口与里程碑", "role_required": "architect", "deps": ["N1"]},
        {"node_key": "N3", "title": "实现与联调", "detail": "完成开发与集成，提交变更说明", "role_required": "developer", "deps": ["N2"]},
        {"node_key": "N4", "title": "测试验收", "detail": "测试用例、回归结果与风险清单", "role_required": "qa", "deps": ["N3"]},
    ]
    if context and isinstance(context, dict):
        _ = context.get("memory_preview", "")
    return {"plan_title": "管家规划任务图", "goal": goal, "nodes": nodes}


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if "```" in raw:
        blocks = raw.split("```")
        for b in blocks:
            candidate = b.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(raw[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def _normalize_plan(obj: dict, *, fallback_goal: str) -> dict:
    plan_title = str(obj.get("plan_title") or "管家规划任务图").strip() or "管家规划任务图"
    goal = str(obj.get("goal") or fallback_goal).strip() or fallback_goal
    raw_nodes = obj.get("nodes")
    if not isinstance(raw_nodes, list):
        return manager_tool_build_plan(goal_text=fallback_goal, context=None)
    nodes: list[dict] = []
    for i, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            continue
        node_key = str(item.get("node_key") or f"N{i + 1}").strip()
        title = str(item.get("title") or f"节点{i + 1}").strip()
        detail = str(item.get("detail") or "").strip()
        role_required = item.get("role_required")
        role_required = str(role_required).strip() if role_required else None
        deps = item.get("deps")
        deps = [str(x).strip() for x in deps] if isinstance(deps, list) else []
        nodes.append(
            {
                "node_key": node_key,
                "title": title,
                "detail": detail,
                "role_required": role_required,
                "deps": [d for d in deps if d],
            }
        )
    if not nodes:
        return manager_tool_build_plan(goal_text=fallback_goal, context=None)
    return {"plan_title": plan_title, "goal": goal, "nodes": nodes}


def _is_off_topic_plan(plan: dict, *, goal_text: str) -> bool:
    goal = str(goal_text or "").strip().lower()
    if not goal:
        return False
    # 当用户目标不是系统排障时，过滤明显偏到“报错排查/落库失败”的规划
    trouble_words = ["落库失败", "排查", "重试", "告警", "诊断", "异常", "ops", "system_admin"]
    if any(w in goal for w in ["报错", "排查", "故障", "异常", "重试"]):
        return False
    text = json.dumps(plan, ensure_ascii=False).lower()
    hit = sum(1 for w in trouble_words if w.lower() in text)
    return hit >= 2


async def manager_tool_build_plan_with_llm(*, db: Session | None = None, goal_text: str, context: dict | None = None) -> dict:
    goal = str(goal_text or "").strip() or "请补充目标交付物定义"
    memory_preview = ""
    if context and isinstance(context, dict):
        memory_preview = str(context.get("memory_preview") or "")
    docs_preview = ""
    if context and isinstance(context, dict):
        docs = context.get("docs_preview") or []
        if isinstance(docs, list):
            docs_preview = "\n".join(
                [f"- {str(d.get('path') or '')}: {str(d.get('preview') or '')}" for d in docs if isinstance(d, dict)]
            )
    prompt = (
        "你是群聊中的管家Agent，只做任务规划，不执行任务。\n"
        "必须严格围绕“用户当前目标”规划，不要被历史错误日志/排障信息带偏。\n"
        "请根据用户目标和群聊长期记忆，输出一个可执行的DAG计划。\n"
        "你必须给出贴合具体领域的节点（避免通用模板：需求/设计/开发/测试 这种空泛拆分），节点要能落到“学评教”场景。\n"
        "必须仅返回JSON对象，不要返回markdown，不要解释。\n"
        "JSON Schema:\n"
        '{\n'
        '  "plan_title": "string",\n'
        '  "goal": "string",\n'
        '  "nodes": [\n'
        '    {"node_key":"N1","title":"string","detail":"string","role_required":"string|null","deps":["N0"]}\n'
        "  ]\n"
        "}\n"
        "约束:\n"
        "1) 节点数 3-8。\n"
        "2) node_key 唯一。\n"
        "3) deps 只能引用已存在节点。\n"
        "4) 输出仅JSON。\n\n"
        f"用户目标:\n{goal}\n\n"
        f"群聊长期记忆(MEMORY.md摘要):\n{memory_preview[:4000]}\n\n"
        f"项目文档摘要:\n{docs_preview[:4000]}"
    )
    # Observability: record that we are going to use LLM for planning (to avoid "looks like template").
    try:
        if db is not None and isinstance(context, dict) and int(context.get("group_id") or 0) > 0:
            from app.services.group_task.event_service import log_group_task_event
            from app.common.event_types import GroupTaskEventType

            # For single-project policy, planning refers to the active/latest run if any; otherwise run_id=0.
            group_id = int(context.get("group_id") or 0)
            active = manager_tool_get_active_run(db, group_id=group_id) if group_id else None
            if active:
                log_group_task_event(
                    db,
                    run_id=int(active.id),
                    node_id=None,
                    event_type=GroupTaskEventType.MANAGER_PLANNING_LLM_STARTED,
                    payload={"goal_preview": goal[:200]},
                    run=None,
                )
    except Exception:
        pass
    # Manager (group capability) must use internal LLM; prefer ReAct loop to enforce tool-first planning.
    if db is not None and isinstance(context, dict) and int(context.get("group_id") or 0) > 0:
        try:
            from app.agent_runtime.manager_runtime import build_plan_with_react_agent

            reply = await build_plan_with_react_agent(
                db=db,
                group_id=int(context.get("group_id") or 0),
                goal_text=goal,
            )
        except Exception:
            reply = await internal_llm_chat(prompt, system_prompt="你是严谨的任务规划助手，只输出合法JSON。")
    else:
        reply = await internal_llm_chat(prompt, system_prompt="你是严谨的任务规划助手，只输出合法JSON。")
    parsed = _extract_json_object(reply)
    if isinstance(parsed, dict):
        plan = _normalize_plan(parsed, fallback_goal=goal)
        if not _is_off_topic_plan(plan, goal_text=goal):
            return plan
    # off-topic 或首次失败，进行一次更强约束重试
    retry_prompt = (
        "仅基于下面用户目标做产品/研发规划，禁止输出任何运维排障/落库失败处理内容。\n"
        "输出JSON对象，字段同前。\n"
        f"用户目标：{goal}\n"
    )
    reply2 = await internal_llm_chat(retry_prompt, system_prompt="只输出与用户目标直接相关的DAG JSON。")
    parsed2 = _extract_json_object(reply2)
    if isinstance(parsed2, dict):
        plan2 = _normalize_plan(parsed2, fallback_goal=goal)
        if not _is_off_topic_plan(plan2, goal_text=goal):
            return plan2
    return manager_tool_build_plan(goal_text=goal, context=context)


def manager_tool_write_plan_run(
    db: Session,
    *,
    group_id: int,
    creator_member_id: int,
    trigger_message_id: int,
    plan: dict,
) -> GroupTaskRun:
    nodes = list(plan.get("nodes") or [])
    title = str(plan.get("plan_title") or "任务计划")
    goal = str(plan.get("goal") or "")
    return create_group_task_run(
        db,
        group_id=int(group_id),
        creator_member_id=int(creator_member_id),
        title=title,
        goal_text=goal,
        nodes=nodes,
        trigger_message_id=int(trigger_message_id),
    )


def manager_tool_get_active_run(db: Session, *, group_id: int) -> GroupTaskRun | None:
    runs = list_group_task_runs(db, group_id=int(group_id))
    if not runs:
        return None
    # single project graph policy: always reuse the latest run
    return runs[0]


def manager_tool_upsert_plan(
    db: Session,
    *,
    group_id: int,
    creator_member_id: int,
    trigger_message_id: int,
    plan: dict,
) -> tuple[str, GroupTaskRun]:
    active = manager_tool_get_active_run(db, group_id=int(group_id))
    if active is None:
        created = manager_tool_write_plan_run(
            db,
            group_id=int(group_id),
            creator_member_id=int(creator_member_id),
            trigger_message_id=int(trigger_message_id),
            plan=plan,
        )
        return "created", created
    updated = update_group_task_dag(db, run_id=int(active.id), nodes=list(plan.get("nodes") or []))
    updated.goal_text = str(plan.get("goal") or updated.goal_text or "")
    updated.title = str(plan.get("plan_title") or updated.title or "任务计划")
    db.add(updated)
    db.commit()
    db.refresh(updated)
    return "updated", updated


async def manager_tool_build_clarify_questions_with_llm(*, goal_text: str, context: dict | None = None) -> list[str]:
    """
    Ask clarifying questions before planning when domain constraints are missing.
    """
    goal = str(goal_text or "").strip()
    memory_preview = ""
    docs_preview = ""
    if isinstance(context, dict):
        memory_preview = str(context.get("memory_preview") or "")
        docs = context.get("docs_preview") or []
        if isinstance(docs, list):
            docs_preview = "\n".join(
                [f"- {str(d.get('path') or '')}: {str(d.get('preview') or '')}" for d in docs if isinstance(d, dict)]
            )
    prompt = (
        "你是群聊项目的管家Agent。用户提出了一个目标，但缺少具体约束。\n"
        "请先提出澄清问题（最多6个），帮助你后续画出DAG计划。\n"
        "要求：问题必须具体、可回答、与目标强相关；不要问泛泛的“还有什么需求”。\n"
        "只输出JSON数组字符串列表，例如：[\"问题1\",\"问题2\"]。\n\n"
        f"目标：{goal}\n\n"
        f"长期记忆摘要：{memory_preview[:2000]}\n\n"
        f"项目文档摘要：{docs_preview[:2000]}\n"
    )
    reply = await internal_llm_chat(prompt, system_prompt="只输出JSON数组。")
    try:
        arr = json.loads(reply)
        if isinstance(arr, list):
            out = [str(x).strip() for x in arr if str(x).strip()]
            return out[:6]
    except Exception:
        pass
    # fallback
    return [
        "目标用户与角色有哪些（学生/教师/管理员/督导）？各自权限是什么？",
        "评教对象与范围是什么（课程/教师/学期/班级）？是否需要匿名？",
        "评价维度与题型需要哪些（量表/选择/文本）？是否支持问卷模板？",
        "流程约束是什么（开放时间/一人一评/必评/补评）？",
        "结果呈现要哪些报表与导出（按教师/课程/学院）？是否要预警/整改闭环？",
        "合规与安全要求有哪些（数据留存、脱敏、审计、权限）？",
    ]
