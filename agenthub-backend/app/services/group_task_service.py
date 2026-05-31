from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.group_task_event import GroupTaskEvent
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.services.storage_paths import project_dir
from app.services.ai_service import ai_chat
from app.services.context_builder import build_project_system_prompt


def _runtime_dir_for_run(group_id: int, run_id: int) -> Path:
    return project_dir(int(group_id)) / "runs" / str(run_id)


def _ensure_group_member(db: Session, *, group_id: int, member_id: int) -> Member:
    member = db.query(Member).filter(Member.id == int(member_id), Member.group_id == int(group_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member not in group")
    return member


MANAGER_MEMBER_NAME = "管家"


def _assistant_is_enabled(db: Session, *, group_id: int) -> bool:
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    return bool(cfg and int(cfg.enabled) == 1)


def get_or_create_manager_member(db: Session, *, group_id: int) -> Member:
    row = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "system", Member.display_name == MANAGER_MEMBER_NAME)
        .first()
    )
    if row:
        return row
    row = Member(
        group_id=int(group_id),
        kind="system",
        display_name=MANAGER_MEMBER_NAME,
        user_ref=None,
        agent_instance_id=None,
        title="group-manager",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_group_assistant_config(db: Session, *, group_id: int, creator_user_id: int) -> GroupAssistantConfig:
    row = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    if row:
        return row
    row = GroupAssistantConfig(
        group_id=int(group_id),
        assistant_agent_instance_id=None,
        enabled=0,
        creator_user_id=int(creator_user_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_group_assistant_config(
    db: Session,
    *,
    group_id: int,
    creator_user_id: int,
    enabled: int,
) -> GroupAssistantConfig:
    row = get_or_create_group_assistant_config(db, group_id=int(group_id), creator_user_id=int(creator_user_id))
    if int(row.creator_user_id) != int(creator_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can update assistant config")
    # Keep legacy column unused for backward compatibility.
    row.assistant_agent_instance_id = None
    row.enabled = 1 if int(enabled) == 1 else 0
    db.add(row)
    db.commit()
    db.refresh(row)
    if int(row.enabled) == 1:
        get_or_create_manager_member(db, group_id=int(group_id))
    return row


def _write_run_files(run: GroupTaskRun, nodes: list[GroupTaskNode]) -> None:
    root = Path(run.runtime_dir)
    root.mkdir(parents=True, exist_ok=True)
    dag = {
        "run_id": int(run.id),
        "group_id": int(run.group_id),
        "title": run.title,
        "goal_text": run.goal_text,
        "status": run.status,
        "nodes": [
            {
                "id": int(n.id),
                "node_key": n.node_key,
                "title": n.title,
                "detail": n.detail,
                "role_required": n.role_required,
                "deps": json.loads(n.deps_json or "[]"),
                "status": n.status,
                "assignee_kind": n.assignee_kind,
                "assignee_member_id": int(n.assignee_member_id) if n.assignee_member_id else None,
                "output_summary": n.output_summary,
                "manager_review_status": n.manager_review_status,
            }
            for n in nodes
        ],
    }
    (root / "dag.json").write_text(json.dumps(dag, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "run.json").write_text(json.dumps({"run": dag}, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_dag_nodes(nodes: list[dict]) -> None:
    if not nodes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DAG nodes cannot be empty")

    keys: list[str] = []
    for item in nodes:
        key = str(item.get("node_key") or "").strip()
        if not key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node_key is required")
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate node_key in DAG")

    key_set = set(keys)
    graph: dict[str, list[str]] = {}
    for item in nodes:
        key = str(item.get("node_key") or "").strip()
        deps = [str(d).strip() for d in (item.get("deps") or []) if str(d).strip()]
        if key in deps:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Node '{key}' cannot depend on itself")
        for d in deps:
            if d not in key_set:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Node '{key}' depends on unknown node_key '{d}'",
                )
        graph[key] = deps

    # Cycle check via DFS (deps graph).
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node_key: str) -> None:
        if node_key in visited:
            return
        if node_key in visiting:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DAG contains a cycle")
        visiting.add(node_key)
        for dep_key in graph.get(node_key, []):
            dfs(dep_key)
        visiting.remove(node_key)
        visited.add(node_key)

    for k in keys:
        dfs(k)


def _append_event_file(run: GroupTaskRun, event: GroupTaskEvent) -> None:
    root = Path(run.runtime_dir) / "events"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "events.jsonl"
    entry = {
        "id": int(event.id),
        "run_id": int(event.run_id),
        "node_id": int(event.node_id) if event.node_id else None,
        "event_type": event.event_type,
        "payload": json.loads(event.payload_json or "{}"),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_group_task_event(db: Session, *, run_id: int, node_id: int | None, event_type: str, payload: dict | None = None) -> GroupTaskEvent:
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    event = GroupTaskEvent(
        run_id=int(run_id),
        node_id=int(node_id) if node_id is not None else None,
        event_type=str(event_type),
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _append_event_file(run, event)
    return event


def create_group_task_run(
    db: Session,
    *,
    group_id: int,
    creator_member_id: int,
    title: str,
    goal_text: str,
    nodes: list[dict],
    trigger_message_id: int | None = None,
) -> GroupTaskRun:
    _validate_dag_nodes(nodes)
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.type != "project":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task runs only supported in project groups")
    _ensure_group_member(db, group_id=int(group_id), member_id=int(creator_member_id))
    if not _assistant_is_enabled(db, group_id=int(group_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group assistant is not enabled")

    run = GroupTaskRun(
        group_id=int(group_id),
        creator_member_id=int(creator_member_id),
        trigger_message_id=int(trigger_message_id) if trigger_message_id else None,
        title=title.strip(),
        goal_text=goal_text.strip(),
        status="planning",
        dag_json="{}",
        runtime_dir="",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run.runtime_dir = _runtime_dir_for_run(int(group_id), int(run.id)).as_posix()
    db.add(run)
    db.commit()
    db.refresh(run)

    node_rows: list[GroupTaskNode] = []
    for item in nodes:
        deps = list(dict.fromkeys([str(d) for d in item.get("deps", [])]))
        node = GroupTaskNode(
            run_id=int(run.id),
            node_key=str(item["node_key"]),
            title=str(item["title"]),
            detail=str(item.get("detail") or ""),
            role_required=str(item.get("role_required")) if item.get("role_required") else None,
            deps_json=json.dumps(deps, ensure_ascii=False),
            status="pending",
            assignee_kind="unclaimed",
            assignee_member_id=None,
            output_summary="",
            manager_review_status="pending",
        )
        db.add(node)
        node_rows.append(node)
    db.commit()
    for node in node_rows:
        db.refresh(node)

    run.status = "executing"
    run.dag_json = json.dumps(
        {
            "nodes": [
                {
                    "node_key": n.node_key,
                    "title": n.title,
                    "role_required": n.role_required,
                    "deps": json.loads(n.deps_json or "[]"),
                }
                for n in node_rows
            ]
        },
        ensure_ascii=False,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _write_run_files(run, node_rows)
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type="run.created",
        payload={"title": run.title, "goal_text": run.goal_text, "node_count": len(node_rows)},
    )
    return run


def list_group_task_runs(db: Session, *, group_id: int) -> list[GroupTaskRun]:
    return (
        db.query(GroupTaskRun)
        .filter(GroupTaskRun.group_id == int(group_id))
        .order_by(GroupTaskRun.id.desc())
        .all()
    )


def get_group_task_run(db: Session, *, run_id: int) -> GroupTaskRun | None:
    return db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()


def list_group_task_nodes(db: Session, *, run_id: int) -> list[GroupTaskNode]:
    return (
        db.query(GroupTaskNode)
        .filter(GroupTaskNode.run_id == int(run_id))
        .order_by(GroupTaskNode.id.asc())
        .all()
    )


def list_group_task_events(db: Session, *, run_id: int) -> list[GroupTaskEvent]:
    return (
        db.query(GroupTaskEvent)
        .filter(GroupTaskEvent.run_id == int(run_id))
        .order_by(GroupTaskEvent.id.asc())
        .all()
    )


def update_group_task_dag(db: Session, *, run_id: int, nodes: list[dict]) -> GroupTaskRun:
    _validate_dag_nodes(nodes)
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if run.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run is immutable")

    current_nodes = list_group_task_nodes(db, run_id=int(run_id))
    node_by_key = {n.node_key: n for n in current_nodes}
    incoming_keys = {str(item["node_key"]) for item in nodes}

    for n in current_nodes:
        if n.node_key not in incoming_keys and n.status in {"pending", "blocked"}:
            db.delete(n)

    for item in nodes:
        key = str(item["node_key"])
        deps = list(dict.fromkeys([str(d) for d in item.get("deps", [])]))
        existing = node_by_key.get(key)
        if existing:
            if existing.status in {"completed", "running"}:
                continue
            existing.title = str(item["title"])
            existing.detail = str(item.get("detail") or "")
            existing.role_required = str(item.get("role_required")) if item.get("role_required") else None
            existing.deps_json = json.dumps(deps, ensure_ascii=False)
            db.add(existing)
        else:
            db.add(
                GroupTaskNode(
                    run_id=int(run.id),
                    node_key=key,
                    title=str(item["title"]),
                    detail=str(item.get("detail") or ""),
                    role_required=str(item.get("role_required")) if item.get("role_required") else None,
                    deps_json=json.dumps(deps, ensure_ascii=False),
                    status="pending",
                    assignee_kind="unclaimed",
                    assignee_member_id=None,
                    output_summary="",
                    manager_review_status="pending",
                )
            )
    db.commit()

    refreshed_nodes = list_group_task_nodes(db, run_id=int(run.id))
    run.dag_json = json.dumps(
        {
            "nodes": [
                {
                    "node_key": n.node_key,
                    "title": n.title,
                    "role_required": n.role_required,
                    "deps": json.loads(n.deps_json or "[]"),
                }
                for n in refreshed_nodes
            ]
        },
        ensure_ascii=False,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _write_run_files(run, refreshed_nodes)
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type="dag.updated",
        payload={"node_count": len(refreshed_nodes)},
    )
    return run


def claim_task_node(db: Session, *, node_id: int, member_id: int) -> GroupTaskNode:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    run = get_group_task_run(db, run_id=int(node.run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    member = _ensure_group_member(db, group_id=int(run.group_id), member_id=int(member_id))

    deps = json.loads(node.deps_json or "[]")
    if deps:
        rows = list_group_task_nodes(db, run_id=int(node.run_id))
        status_by_key = {r.node_key: r.status for r in rows}
        unmet = [d for d in deps if status_by_key.get(d) != "completed"]
        if unmet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dependencies not completed: {', '.join(unmet)}")

    node.assignee_member_id = int(member.id)
    node.assignee_kind = "agent" if member.kind == "agent" else "user"
    node.status = "running"
    db.add(node)
    db.commit()
    db.refresh(node)
    run_rows = list_group_task_nodes(db, run_id=int(run.id))
    _write_run_files(run, run_rows)
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.claimed",
        payload={"member_id": int(member.id), "assignee_kind": node.assignee_kind},
    )
    return node


def auto_assign_pending_nodes(db: Session, *, run_id: int) -> int:
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        return 0
    rows = list_group_task_nodes(db, run_id=int(run.id))
    members = db.query(Member).filter(Member.group_id == int(run.group_id)).all()
    role_agents: dict[str, Member] = {}
    role_users: dict[str, Member] = {}
    for m in members:
        title = str(m.title or "").strip().lower()
        if not title:
            continue
        if m.kind == "agent" and title not in role_agents:
            role_agents[title] = m
        if m.kind == "user" and title not in role_users:
            role_users[title] = m
    changed = 0
    for n in rows:
        if n.status != "pending":
            continue
        role = str(n.role_required or "").strip().lower()
        if not role:
            continue
        assignee = role_agents.get(role) or role_users.get(role)
        if not assignee:
            continue
        deps = json.loads(n.deps_json or "[]")
        status_by_key = {r.node_key: r.status for r in rows}
        if any(status_by_key.get(d) != "completed" for d in deps):
            continue
        n.assignee_member_id = int(assignee.id)
        n.assignee_kind = "agent" if assignee.kind == "agent" else "user"
        if assignee.kind == "agent":
            n.status = "running"
        db.add(n)
        changed += 1
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(n.id),
            event_type="node.auto_assigned",
            payload={"member_id": int(assignee.id), "assignee_kind": n.assignee_kind, "role_required": role},
        )
    if changed > 0:
        db.commit()
        _write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
    return changed


def complete_task_node(db: Session, *, node_id: int, member_id: int, output_summary: str) -> GroupTaskNode:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if not node.assignee_member_id or int(node.assignee_member_id) != int(member_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assignee can complete this node")
    node.status = "completed"
    node.output_summary = output_summary.strip()
    node.manager_review_status = "pending"
    db.add(node)
    db.commit()
    db.refresh(node)
    run = get_group_task_run(db, run_id=int(node.run_id))
    if run:
        run_rows = list_group_task_nodes(db, run_id=int(run.id))
        if run_rows and all(r.status == "completed" and r.manager_review_status == "approved" for r in run_rows):
            run.status = "completed"
            db.add(run)
            db.commit()
            db.refresh(run)
        _write_run_files(run, run_rows)
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type="node.completed",
            payload={"assignee_member_id": int(member_id)},
        )
    return node


def review_task_node(db: Session, *, node_id: int, manager_review_status: str, note: str = "") -> GroupTaskNode:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if node.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Node is not completed")
    node.manager_review_status = manager_review_status
    if manager_review_status == "rework":
        node.status = "running"
        if note.strip():
            node.output_summary = f"{node.output_summary}\n\n[Manager Rework Note]\n{note.strip()}"
    db.add(node)
    db.commit()
    db.refresh(node)
    run = get_group_task_run(db, run_id=int(node.run_id))
    if run:
        run_rows = list_group_task_nodes(db, run_id=int(run.id))
        if run_rows and all(r.status == "completed" and r.manager_review_status == "approved" for r in run_rows):
            run.status = "completed"
        else:
            run.status = "executing"
        db.add(run)
        db.commit()
        db.refresh(run)
        _write_run_files(run, run_rows)
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type="node.reviewed",
            payload={"manager_review_status": manager_review_status, "note": note},
        )
        role_required = str(node.role_required or "").strip()
        if role_required:
            if manager_review_status == "rework":
                block_role_branch_nodes(
                    db,
                    run_id=int(run.id),
                    role_required=role_required,
                    reason=f"manager_rework:{node.node_key}",
                )
            elif manager_review_status == "approved":
                unblock_role_branch_nodes(
                    db,
                    run_id=int(run.id),
                    role_required=role_required,
                    reason=f"manager_approved:{node.node_key}",
                )
    return node


async def auto_review_completed_node(db: Session, *, node_id: int) -> GroupTaskNode | None:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node:
        return None
    if node.status != "completed" or node.manager_review_status != "pending":
        return node

    run = get_group_task_run(db, run_id=int(node.run_id))
    if not run:
        return node
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(run.group_id)).first()
    if not cfg or int(cfg.enabled) != 1:
        return node
    manager_member = get_or_create_manager_member(db, group_id=int(run.group_id))
    if not manager_member:
        return node
    # Group-native manager uses simple deterministic heuristic for now.
    text = str(node.output_summary or "").strip().lower()
    blocked_words = ["todo", "待补充", "unknown", "不确定", "后续", "未完成"]
    if any(w.lower() in text for w in blocked_words):
        decision = "rework"
        note = "完成总结包含未完成/不确定项，请补充后再提交。"
    else:
        decision = "approved"
        note = "完成总结满足节点要求，已通过。"

    reviewed = review_task_node(
        db,
        node_id=int(node.id),
        manager_review_status=decision,
        note=note,
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(reviewed.id),
        event_type="node.auto_reviewed",
        payload={"decision": decision, "note": note},
    )
    try:
        _ = auto_assign_pending_nodes(db, run_id=int(run.id))
    except Exception:
        pass
    return reviewed


async def run_agent_for_node(db: Session, *, node_id: int) -> GroupTaskNode | None:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node or node.status != "running":
        return node
    if node.assignee_kind != "agent" or not node.assignee_member_id:
        return node
    member = db.query(Member).filter(Member.id == int(node.assignee_member_id)).first()
    if not member or not member.agent_instance_id:
        return node
    run = get_group_task_run(db, run_id=int(node.run_id))
    if not run:
        return node
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.exec.started",
        payload={"node_key": node.node_key, "title": node.title},
    )
    agent_id = int(member.agent_instance_id)
    system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(run.group_id))
    prompt = (
        f"你负责执行DAG节点任务。\n"
        f"node_key={node.node_key}\n"
        f"title={node.title}\n"
        f"detail={node.detail}\n"
        "请输出该节点执行总结，包含产出、风险、下一步。"
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.exec.thinking",
        payload={"step": "analyze_task", "prompt_preview": prompt[:300]},
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.exec.tool_call",
        payload={"tool": "llm.chat", "model": "project-default", "purpose": "execute_node_task"},
    )
    summary = await ai_chat(
        prompt,
        system_prompt=system_prompt,
        agent_instance_id=agent_id,
        runtime_context={"group_type": "project", "group_id": int(run.group_id)},
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.exec.tool_result",
        payload={"tool": "llm.chat", "ok": True, "output_chars": len(summary or "")},
    )
    chunks = [s.strip() for s in str(summary or "").replace("\n", " ").split("。") if s.strip()]
    for idx, ch in enumerate(chunks[:8]):
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type="node.exec.stream_chunk",
            payload={"index": idx, "text": ch[:220]},
        )
    completed = complete_task_node(db, node_id=int(node.id), member_id=int(member.id), output_summary=summary or "节点执行完成")
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type="node.exec.finished",
        payload={"status": completed.status, "manager_review_status": completed.manager_review_status},
    )
    return completed


def block_role_branch_nodes(db: Session, *, run_id: int, role_required: str, reason: str) -> int:
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    rows = list_group_task_nodes(db, run_id=int(run.id))
    changed = 0
    for n in rows:
        if (n.role_required or "") != str(role_required):
            continue
        # Only block not-started nodes in this role branch.
        if n.status not in {"pending"}:
            continue
        if n.status != "blocked":
            n.status = "blocked"
            db.add(n)
            changed += 1
    db.commit()
    if changed > 0:
        _write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=None,
            event_type="branch.blocked",
            payload={"role_required": role_required, "reason": reason, "count": changed},
        )
    return changed


def unblock_role_branch_nodes(db: Session, *, run_id: int, role_required: str, reason: str) -> int:
    run = get_group_task_run(db, run_id=int(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    rows = list_group_task_nodes(db, run_id=int(run.id))
    changed = 0
    for n in rows:
        if (n.role_required or "") != str(role_required):
            continue
        if n.status == "blocked":
            n.status = "pending"
            db.add(n)
            changed += 1
    db.commit()
    if changed > 0:
        _write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=None,
            event_type="branch.unblocked",
            payload={"role_required": role_required, "reason": reason, "count": changed},
        )
    return changed
