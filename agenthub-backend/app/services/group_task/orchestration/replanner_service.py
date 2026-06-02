from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agent_runtime.message_store import create_message
from app.common.event_types import GroupTaskEventType
from app.models.group_task_event import GroupTaskEvent
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.services._zero_deps_ai_helpers import simple_internal_llm_chat as internal_llm_chat
from app.services.group_task.event_service import log_group_task_event
from app.services.group_task.node_service import list_group_task_nodes, update_group_task_dag


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if "```" in raw:
        for b in raw.split("```"):
            c = b.strip()
            if c.startswith("json"):
                c = c[4:].strip()
            if c.startswith("{") and c.endswith("}"):
                try:
                    obj = json.loads(c)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    s = raw.find("{")
    e = raw.rfind("}")
    if s >= 0 and e > s:
        try:
            obj = json.loads(raw[s : e + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _normalize_plan(obj: dict, *, fallback_goal: str) -> dict:
    plan_title = str(obj.get("plan_title") or "重规划任务图").strip() or "重规划任务图"
    goal = str(obj.get("goal") or fallback_goal).strip() or fallback_goal
    raw_nodes = obj.get("nodes")
    if not isinstance(raw_nodes, list):
        return {"plan_title": plan_title, "goal": goal, "nodes": []}
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
    return {"plan_title": plan_title, "goal": goal, "nodes": nodes}


def _node_result_brief(n: GroupTaskNode) -> dict:
    brief = {
        "node_key": str(n.node_key),
        "title": str(n.title),
        "status": str(n.status),
        "manager_review_status": str(n.manager_review_status),
    }
    try:
        rj = json.loads(str(getattr(n, "result_json", "") or "{}"))
        if isinstance(rj, dict) and rj:
            brief["result"] = {
                "status": rj.get("status"),
                "summary": str(rj.get("summary") or "")[:300],
                "issues": rj.get("issues") if isinstance(rj.get("issues"), list) else [],
                "suggested_ops": rj.get("suggested_ops") if isinstance(rj.get("suggested_ops"), list) else [],
            }
    except Exception:
        pass
    return brief


async def maybe_replan_unstarted_nodes(
    db: Session,
    *,
    run_id: int,
    trigger: str,
    reason: str,
    max_nodes: int = 8,
) -> bool:
    run = db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()
    if not run:
        return False

    try:
        latest = (
            db.query(GroupTaskEvent)
            .filter(GroupTaskEvent.run_id == int(run.id), GroupTaskEvent.event_type.in_([GroupTaskEventType.RUN_REPLAN_STARTED, GroupTaskEventType.RUN_REPLAN_APPLIED]))
            .order_by(GroupTaskEvent.id.desc())
            .first()
        )
        if latest and latest.created_at:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if (now - latest.created_at).total_seconds() < 30:
                return False
    except Exception:
        pass

    nodes = list_group_task_nodes(db, run_id=int(run.id))
    has_problem = any((str(n.manager_review_status) == "rework") or (str(n.status) in {"failed"}) for n in nodes)
    has_suggested_ops = False
    for n in nodes:
        try:
            rj = json.loads(str(getattr(n, "result_json", "") or "{}"))
            if isinstance(rj, dict) and isinstance(rj.get("suggested_ops"), list) and rj.get("suggested_ops"):
                has_suggested_ops = True
                break
        except Exception:
            continue
    if not (has_problem or has_suggested_ops):
        return False

    completed = [n for n in nodes if str(n.status) == "completed"]
    unstarted = [n for n in nodes if str(n.status) in {"pending", "blocked"}]
    if not unstarted:
        return False

    completed_brief = [_node_result_brief(n) for n in completed][-12:]
    unstarted_brief = [_node_result_brief(n) for n in unstarted][:12]

    prompt = (
        "你是群聊项目的管家Agent，现在需要基于执行结果对后续未执行节点进行重规划（只改未开始的节点）。\n"
        "输入包含：项目目标、已完成节点摘要、未开始节点摘要、以及触发原因。\n"
        "输出必须仅JSON对象，不要markdown，不要解释。\n"
        "JSON schema：{plan_title, goal, nodes:[{node_key,title,detail,role_required,deps}]}\n"
        "要求：\n"
        "1) 保持已完成节点 node_key 不变（你可以在 deps 引用它们）。\n"
        "2) 只规划 3-8 个节点，覆盖未开始部分；必要时可新增节点或拆分。\n"
        "3) deps 只能引用输出中已有节点或已完成节点。\n\n"
        f"项目目标：{run.goal_text}\n"
        f"触发：{trigger}\n原因：{reason}\n\n"
        f"已完成节点摘要：{json.dumps(completed_brief, ensure_ascii=False)}\n\n"
        f"未开始节点摘要：{json.dumps(unstarted_brief, ensure_ascii=False)}\n"
    )

    try:
        reply = await internal_llm_chat(prompt, system_prompt="只输出严格JSON。")
    except Exception:
        return False
    obj = _extract_json_object(reply)
    if not isinstance(obj, dict):
        return False
    plan = _normalize_plan(obj, fallback_goal=str(run.goal_text or ""))
    if not plan.get("nodes"):
        return False

    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type=GroupTaskEventType.RUN_REPLAN_STARTED,
        payload={"trigger": trigger, "reason": reason},
    )
    _ = update_group_task_dag(db, run_id=int(run.id), nodes=list(plan.get("nodes") or [])[: max_nodes])
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type=GroupTaskEventType.RUN_REPLAN_APPLIED,
        payload={"node_count": len(list(plan.get("nodes") or []))},
    )
    return True
