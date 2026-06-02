from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.common.event_types import GroupTaskEventType
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.services.group_task.event_service import log_group_task_event
from app.services.group_task.node_service import list_group_task_nodes


def _deps_met(nodes: list[GroupTaskNode], node: GroupTaskNode) -> bool:
    try:
        deps = json.loads(node.deps_json or "[]")
    except Exception:
        deps = []
    if not deps:
        return True
    status_by_key = {n.node_key: n.status for n in nodes}
    return all(status_by_key.get(str(d)) == "completed" for d in deps)


def _candidate_members(db: Session, *, group_id: int) -> list[Member]:
    return db.query(Member).filter(Member.group_id == int(group_id)).order_by(Member.id.asc()).all()


def _extract_json_object(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    # Try fenced JSON blocks
    if "```" in raw:
        for b in raw.split("```"):
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
    # Direct JSON object
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    # Best-effort substring
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(raw[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


async def smart_auto_assign_pending_nodes(db: Session, *, run_id: int, max_nodes: int = 12) -> int:
    """
    LLM-assisted auto assignment.

    - Only assigns nodes that are still pending & unclaimed.
    - Only assigns nodes whose deps are met.
    - Never assigns to non-members.
    - Prefers agent members when reasonable, but can assign to user members too.
    """
    run = db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()
    if not run:
        return 0

    nodes = list_group_task_nodes(db, run_id=int(run.id))
    pending = [
        n
        for n in nodes
        if n.status == "pending" and str(n.assignee_kind or "") == "unclaimed" and n.assignee_member_id is None and _deps_met(nodes, n)
    ]
    if not pending:
        return 0
    pending = pending[: max(1, int(max_nodes))]

    # Auto-assignment is for runnable subagents only. Users should claim manually.
    members = [m for m in _candidate_members(db, group_id=int(run.group_id)) if str(m.kind) == "agent" and m.agent_instance_id]
    candidates: list[dict] = []
    for m in members:
        candidates.append(
            {
                "member_id": int(m.id),
                "kind": str(m.kind),
                "display_name": str(m.display_name or ""),
                "title": str(m.title or ""),
                "agent_instance_id": int(m.agent_instance_id) if m.agent_instance_id else None,
            }
        )

    node_specs: list[dict] = []
    for n in pending:
        node_specs.append(
            {
                "node_key": str(n.node_key),
                "title": str(n.title),
                "detail": str(n.detail or "")[:800],
                "role_required": str(n.role_required or ""),
            }
        )

    prompt = (
        "你是群聊项目的任务分配器。你要把待执行的DAG节点分配给群成员。\n"
        "注意：role_required 可能是模糊/同义词（如 backend / 后端 / 后端开发 / server），你需要智能匹配。\n"
        "约束：\n"
        "1) 只能从候选成员列表中选择 member_id；也允许 member_id=null 表示暂不分配（留给人工认领）。\n"
        "2) 优先分配给 kind=agent 且 agent_instance_id!=null 的成员；如果只有用户更合适也可分配给用户。\n"
        "3) 不要编造成员，不要输出解释，只输出JSON。\n"
        "输出JSON schema：\n"
        '{ "assignments": [ { "node_key": "N1", "member_id": 123|null, "reason": "..." } ] }\n\n'
        f"候选成员：\n{json.dumps(candidates, ensure_ascii=False)}\n\n"
        f"待分配节点：\n{json.dumps(node_specs, ensure_ascii=False)}\n"
    )

    try:
        reply = await internal_llm_chat(prompt, system_prompt="只输出严格JSON。")
    except Exception:
        return 0
    obj = _extract_json_object(reply)
    if not isinstance(obj, dict):
        return 0
    items = obj.get("assignments")
    if not isinstance(items, list):
        return 0
    candidate_ids = {int(c["member_id"]) for c in candidates if isinstance(c, dict) and c.get("member_id") is not None}

    by_key = {n.node_key: n for n in pending}
    member_by_id = {int(m.id): m for m in members}
    changed = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        node_key = str(it.get("node_key") or "").strip()
        if not node_key or node_key not in by_key:
            continue
        raw_member_id = it.get("member_id")
        member_id = None
        if raw_member_id is not None and str(raw_member_id).strip() != "":
            try:
                member_id = int(raw_member_id)
            except Exception:
                member_id = None
        if member_id is None:
            continue
        if member_id not in candidate_ids:
            continue
        node = by_key[node_key]
        # Re-check still assignable (race-safe-ish)
        if node.status != "pending" or node.assignee_member_id is not None or str(node.assignee_kind or "") != "unclaimed":
            continue
        m = member_by_id.get(int(member_id))
        if not m:
            continue

        node.assignee_member_id = int(m.id)
        node.assignee_kind = "agent" if str(m.kind) == "agent" else "user"
        if str(m.kind) == "agent" and m.agent_instance_id:
            node.status = "running"
        db.add(node)
        changed += 1
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type=GroupTaskEventType.NODE_SMART_AUTO_ASSIGNED,
            payload={
                "member_id": int(m.id),
                "assignee_kind": node.assignee_kind,
                "role_required": str(node.role_required or ""),
                "reason": str(it.get("reason") or "")[:400],
            },
        )
    if changed:
        db.commit()
    return int(changed)
