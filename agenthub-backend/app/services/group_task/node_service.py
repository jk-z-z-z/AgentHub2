from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.event_types import GroupTaskEventType
from app.models.group import Group
from app.models.group_assistant_config import GroupAssistantConfig
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.models.agent_instance import AgentInstance
from app.agent_runtime.agent_run_executor import execute_agent_run
from app.agent_runtime.memory_builder import build_project_system_prompt
from app.services.group_task.event_service import list_group_task_events, log_group_task_event
from app.services.group_task.helpers import assistant_is_enabled, ensure_group_member, runtime_dir_for_run, validate_dag_nodes, write_run_files
from app.services.group_task.manager_service import get_or_create_manager_member
from app.services.storage_paths import project_dir
from app.agent_runtime.tools.executor import execute_builtin_tool
from app.services.group_orchestrator.graph_service import build_graph_snapshot, upsert_graph_snapshot




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
    validate_dag_nodes(nodes)
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.type != "project":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task runs only supported in project groups")
    ensure_group_member(db, group_id=int(group_id), member_id=int(creator_member_id))
    if not assistant_is_enabled(db, group_id=int(group_id)):
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

    run.runtime_dir = runtime_dir_for_run(int(group_id), int(run.id)).as_posix()
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
    # Graph snapshot v1
    try:
        snapshot = build_graph_snapshot(run_id=int(run.id), nodes=node_rows, goal=run.goal_text, version=1)
        _ = upsert_graph_snapshot(db, run_id=int(run.id), version=1, snapshot=snapshot)
    except Exception:
        pass
    write_run_files(run, node_rows)
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type=GroupTaskEventType.RUN_CREATED,
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


def update_group_task_dag(db: Session, *, run_id: int, nodes: list[dict]) -> GroupTaskRun:
    validate_dag_nodes(nodes)
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
    write_run_files(run, refreshed_nodes)
    try:
        from app.models.group_task_graph import GroupTaskGraph

        latest = (
            db.query(GroupTaskGraph)
            .filter(GroupTaskGraph.run_id == int(run.id))
            .order_by(GroupTaskGraph.version.desc())
            .first()
        )
        ver = int(latest.version) + 1 if latest else 1
        snapshot = build_graph_snapshot(run_id=int(run.id), nodes=refreshed_nodes, goal=run.goal_text, version=ver)
        _ = upsert_graph_snapshot(db, run_id=int(run.id), version=ver, snapshot=snapshot)
    except Exception:
        pass
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=None,
        event_type=GroupTaskEventType.DAG_UPDATED,
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
    member = ensure_group_member(db, group_id=int(run.group_id), member_id=int(member_id))

    deps = json.loads(node.deps_json or "[]")
    if deps:
        rows = list_group_task_nodes(db, run_id=int(node.run_id))
        status_by_key = {r.node_key: r.status for r in rows}
        unmet = [d for d in deps if status_by_key.get(d) != "completed"]
        if unmet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dependencies not completed: {', '.join(unmet)}")

    node.assignee_member_id = int(member.id)
    node.assignee_kind = "agent" if member.kind == "agent" else "user"
    # Only agent assignees are executed by scheduler automatically.
    # User assignees should remain pending until they manually complete.
    node.status = "running" if member.kind == "agent" else "pending"
    db.add(node)
    db.commit()
    db.refresh(node)
    run_rows = list_group_task_nodes(db, run_id=int(run.id))
    write_run_files(run, run_rows)
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_CLAIMED,
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
    for m in members:
        title = str(m.title or "").strip().lower()
        if not title:
            continue
        if m.kind == "agent" and m.agent_instance_id and title not in role_agents:
            role_agents[title] = m
    changed = 0
    for n in rows:
        if n.status != "pending":
            continue
        role = str(n.role_required or "").strip().lower()
        if not role:
            continue
        # Auto-assign only to runnable agent members. Users should claim manually.
        assignee = role_agents.get(role)
        if not assignee:
            continue
        deps = json.loads(n.deps_json or "[]")
        status_by_key = {r.node_key: r.status for r in rows}
        if any(status_by_key.get(d) != "completed" for d in deps):
            continue
        n.assignee_member_id = int(assignee.id)
        n.assignee_kind = "agent"
        n.status = "running"
        db.add(n)
        changed += 1
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(n.id),
            event_type=GroupTaskEventType.NODE_AUTO_ASSIGNED,
            payload={"member_id": int(assignee.id), "assignee_kind": n.assignee_kind, "role_required": role},
        )
    if changed > 0:
        db.commit()
        write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
    return changed


def complete_task_node(db: Session, *, node_id: int, member_id: int, output_summary: str) -> GroupTaskNode:
    node = db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if not node.assignee_member_id or int(node.assignee_member_id) != int(member_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assignee can complete this node")
    node.status = "completed"
    node.output_summary = output_summary.strip()
    # Persist structured result in result_json (for machine-readable receipts).
    try:
        from app.services.group_orchestrator.node_protocol import parse_node_result

        nr = parse_node_result(output_summary)
        node.result_json = json.dumps(
            {
                "node_id": int(node.id),
                "node_key": node.node_key,
                "status": nr.status,
                "summary": nr.summary or node.output_summary[:400],
                "deliverables": nr.deliverables,
                "evidence": nr.evidence,
                "confidence": nr.confidence,
                "issues": nr.issues,
                "suggested_ops": nr.suggested_ops,
                "invalidates_node_id": nr.invalidates_node_id,
                "supersedes_node_id": nr.supersedes_node_id,
            },
            ensure_ascii=False,
        )
    except Exception:
        node.result_json = json.dumps({}, ensure_ascii=False)
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
        write_run_files(run, run_rows)
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type=GroupTaskEventType.NODE_COMPLETED,
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
        write_run_files(run, run_rows)
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type=GroupTaskEventType.NODE_REVIEWED,
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
        event_type=GroupTaskEventType.NODE_AUTO_REVIEWED,
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
        event_type=GroupTaskEventType.NODE_EXEC_STARTED,
        payload={"node_key": node.node_key, "title": node.title},
    )
    agent_id = int(member.agent_instance_id)
    system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(run.group_id))
    prompt = (
        f"你负责执行DAG节点任务。\n"
        f"node_key={node.node_key}\n"
        f"title={node.title}\n"
        f"detail={node.detail}\n"
        "请输出 NodeResult JSON（不要解释，不要markdown），字段：\n"
        '{\n'
        '  "node_id": number,\n'
        '  "node_key": string,\n'
        '  "status": "succeeded"|"failed",\n'
        '  "summary": string,\n'
        '  "deliverables": [{"type": "file|text|link|data", "value": "..."}],\n'
        '  "evidence": [{"type": "tool|file|message", "ref": "...", "note": "..."}],\n'
        '  "confidence": 0.0,\n'
        '  "issues": [string],\n'
        '  "suggested_ops": [{"op":"retry_node|reassign_node|split_node|add_node|insert_judge_node","args":{}}]\n'
        '}\n'
        "约束：\n"
        "1) 只输出JSON对象。\n"
        "2) deliverables/evidence 尽量提供可验证引用。\n"
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_EXEC_THINKING,
        payload={"step": "analyze_task", "prompt_preview": prompt[:300]},
    )
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_EXEC_TOOL_CALL,
        payload={"tool": "llm.chat", "model": "project-default", "purpose": "execute_node_task"},
    )

    def _tool_exec(tool_code: str, args: dict) -> dict:
        return execute_builtin_tool(
            agent_id=int(agent_id),
            tool_code=tool_code,
            args=args or {},
            runtime_context={
                "group_type": "project",
                "group_id": int(run.group_id),
                "run_id": int(run.id),
                "node_id": int(node.id),
            },
        )

    exec_res = await execute_agent_run(
        db,
        group_id=int(run.group_id),
        agent_instance_id=int(agent_id),
        input_text=prompt,
        system_prompt=system_prompt,
        runtime_context={
            "group_type": "project",
            "group_id": int(run.group_id),
            "run_id": int(run.id),
            "node_id": int(node.id),
            "project_code_cwd": str(project_dir(int(run.group_id)) / "shared" / "code"),
        },
        trigger_message_id=int(run.trigger_message_id) if run.trigger_message_id else None,
        mode="dag_node",
        group_task_run_id=int(run.id),
        group_task_node_id=int(node.id),
        tool_executor=_tool_exec,
    )
    summary = exec_res.result.text or "节点执行完成"
    node.agent_run_id = int(exec_res.run.id)
    db.add(node)
    db.commit()
    # Validate deliverables that claim files: they must actually exist in project shared code root.
    try:
        from app.services.group_orchestrator.node_protocol import parse_node_result
        from app.services.group_orchestrator.deliverable_validator import validate_deliverable_files

        nr = parse_node_result(summary)
        proj_root = (project_dir(int(run.group_id)) / "shared" / "code").resolve()
        filtered, issues = validate_deliverable_files(project_root=proj_root, deliverables=nr.deliverables)
        if issues:
            # Patch the output so persisted result_json/receipt won't claim nonexistent files.
            nr.deliverables = filtered
            nr.issues = list(dict.fromkeys([*nr.issues, *issues]))
            summary = json.dumps(
                {
                    "node_id": int(node.id),
                    "node_key": node.node_key,
                    "status": nr.status,
                    "summary": nr.summary or "",
                    "deliverables": nr.deliverables,
                    "evidence": nr.evidence,
                    "confidence": nr.confidence,
                    "issues": nr.issues,
                    "suggested_ops": nr.suggested_ops,
                },
                ensure_ascii=False,
            )
    except Exception:
        pass
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_EXEC_TOOL_RESULT,
        payload={"tool": "llm.chat", "ok": True, "output_chars": len(summary or "")},
    )
    chunks = [s.strip() for s in str(summary or "").replace("\n", " ").split("。") if s.strip()]
    for idx, ch in enumerate(chunks[:8]):
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=int(node.id),
            event_type=GroupTaskEventType.NODE_EXEC_STREAM_CHUNK,
            payload={"index": idx, "text": ch[:220]},
        )
    completed = complete_task_node(db, node_id=int(node.id), member_id=int(member.id), output_summary=summary or "节点执行完成")
    # Post one compact node receipt message (no spam). This is the only mandatory chat output.
    try:
        from app.services.group_orchestrator.receipt_writer import post_node_receipt_message

        await post_node_receipt_message(
            db,
            run=run,
            node=completed,
            assignee_member=member,
            reply_to_message_id=int(run.trigger_message_id) if run.trigger_message_id else None,
        )
    except Exception:
        pass
    log_group_task_event(
        db,
        run_id=int(run.id),
        node_id=int(node.id),
        event_type=GroupTaskEventType.NODE_EXEC_FINISHED,
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
        write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=None,
            event_type=GroupTaskEventType.BRANCH_BLOCKED,
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
        write_run_files(run, list_group_task_nodes(db, run_id=int(run.id)))
        log_group_task_event(
            db,
            run_id=int(run.id),
            node_id=None,
            event_type=GroupTaskEventType.BRANCH_UNBLOCKED,
            payload={"role_required": role_required, "reason": reason, "count": changed},
        )
    return changed
