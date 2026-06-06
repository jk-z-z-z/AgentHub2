from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.models.message_event import MessageEvent


TERMINAL_STATUSES = {"completed", "failed", "blocked"}


@dataclass(frozen=True)
class DagPatchResult:
    group_id: int
    run_id: int
    node_count: int
    edge_count: int
    created_node_keys: list[str]
    updated_node_keys: list[str]
    deleted_node_keys: list[str]


def ensure_group_member(db: Session, *, group_id: int, member_id: int) -> Member:
    member = db.query(Member).filter(Member.id == int(member_id), Member.group_id == int(group_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member not in group")
    return member


def get_run(db: Session, *, run_id: int) -> GroupTaskRun | None:
    return db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()


def resolve_run(db: Session, *, run_id: int) -> GroupTaskRun:
    row = get_run(db, run_id=int(run_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task run not found")
    return row


def list_runs(db: Session, *, group_id: int) -> list[GroupTaskRun]:
    return (
        db.query(GroupTaskRun)
        .filter(GroupTaskRun.group_id == int(group_id))
        .order_by(GroupTaskRun.id.desc())
        .all()
    )


def validate_dag_nodes(nodes: list[dict]) -> None:
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
        deps = [str(dep).strip() for dep in (item.get("deps") or []) if str(dep).strip()]
        if key in deps:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Node '{key}' cannot depend on itself")
        for dep in deps:
            if dep not in key_set:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Node '{key}' depends on unknown node_key '{dep}'",
                )
        graph[key] = deps

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

    for key in keys:
        dfs(key)


def _normalize_node_payload(item: dict) -> dict:
    node_key = str(item.get("node_key") or "").strip()
    title = str(item.get("title") or "").strip()
    detail = str(item.get("detail") or "").strip()
    role_required = item.get("role_required")
    role_required = str(role_required).strip() if role_required else None
    parent_node_key = item.get("parent_node_key")
    parent_node_key = str(parent_node_key).strip() if parent_node_key else None
    deps = item.get("deps")
    deps = [str(dep).strip() for dep in deps] if isinstance(deps, list) else []
    return {
        "node_key": node_key,
        "title": title,
        "detail": detail,
        "role_required": role_required,
        "parent_node_key": parent_node_key,
        "deps": [dep for dep in dict.fromkeys(deps) if dep],
    }


def _normalize_node_changes(changes: dict) -> dict:
    deps = changes.get("deps")
    deps = [str(dep).strip() for dep in deps] if isinstance(deps, list) else None
    parent_node_key = changes.get("parent_node_key")
    parent_node_key = str(parent_node_key).strip() if parent_node_key else None
    title = changes.get("title")
    detail = changes.get("detail")
    role_required = changes.get("role_required")
    return {
        "title": str(title).strip() if title is not None else None,
        "detail": str(detail).strip() if detail is not None else None,
        "role_required": str(role_required).strip() if role_required is not None and str(role_required).strip() else None,
        "parent_node_key": parent_node_key,
        "deps": [dep for dep in dict.fromkeys(deps or []) if dep] if deps is not None else None,
    }


def list_nodes(db: Session, *, run_id: int) -> list[GroupTaskNode]:
    return (
        db.query(GroupTaskNode)
        .filter(GroupTaskNode.run_id == int(run_id))
        .order_by(GroupTaskNode.id.asc())
        .all()
    )


def get_node(db: Session, *, node_id: int) -> GroupTaskNode | None:
    return db.query(GroupTaskNode).filter(GroupTaskNode.id == int(node_id)).first()


def get_node_by_key(db: Session, *, run_id: int, node_key: str) -> GroupTaskNode | None:
    return (
        db.query(GroupTaskNode)
        .filter(GroupTaskNode.run_id == int(run_id), GroupTaskNode.node_key == str(node_key))
        .first()
    )


def _deps_from_row(row: GroupTaskNode) -> list[str]:
    try:
        payload = json.loads(row.input_json or "{}")
    except Exception:
        payload = {}
    deps = payload.get("deps") if isinstance(payload, dict) else []
    if not isinstance(deps, list):
        return []
    return [str(dep).strip() for dep in deps if str(dep).strip()]


def _parent_key_from_row(row: GroupTaskNode, rows_by_id: dict[int, GroupTaskNode]) -> str | None:
    if not row.parent_node_id:
        return None
    parent = rows_by_id.get(int(row.parent_node_id))
    return parent.node_key if parent else None


def _row_snapshot(row: GroupTaskNode, rows_by_id: dict[int, GroupTaskNode]) -> dict[str, Any]:
    deps = _deps_from_row(row)
    return {
        "id": int(row.id),
        "group_id": int(row.group_id),
        "run_id": int(row.run_id),
        "parent_node_id": int(row.parent_node_id) if row.parent_node_id else None,
        "parent_node_key": _parent_key_from_row(row, rows_by_id),
        "node_key": row.node_key,
        "title": row.title,
        "detail": row.detail,
        "role_required": row.role_required,
        "status": row.status,
        "assignee_kind": row.assignee_kind,
        "assignee_member_id": int(row.assignee_member_id) if row.assignee_member_id else None,
        "attempt": int(row.attempt or 0),
        "deps": deps,
        "input_json": row.input_json,
        "result_json": row.result_json,
        "error": row.error,
        "output_summary": row.output_summary,
        "manager_review_status": row.manager_review_status,
        "manager_review_note": row.manager_review_note,
        "reviewed_at": row.reviewed_at,
        "reviewed_by_member_id": int(row.reviewed_by_member_id) if row.reviewed_by_member_id else None,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def get_dag_view(db: Session, *, run_id: int) -> dict[str, Any]:
    run = resolve_run(db, run_id=int(run_id))
    rows = list_nodes(db, run_id=int(run_id))
    rows_by_id = {int(row.id): row for row in rows}
    nodes = [_row_snapshot(row, rows_by_id) for row in rows]
    nodes_by_key = {row.node_key: row for row in rows}
    edges: list[dict[str, str]] = []
    for row in rows:
        for dep_key in _deps_from_row(row):
            if dep_key in nodes_by_key:
                edges.append({"from": dep_key, "to": row.node_key})
    return {"run_id": str(run.id), "nodes": nodes, "edges": edges}


def list_node_snapshots(db: Session, *, run_id: int) -> list[dict[str, Any]]:
    rows = list_nodes(db, run_id=int(run_id))
    rows_by_id = {int(row.id): row for row in rows}
    return [_row_snapshot(row, rows_by_id) for row in rows]


def node_snapshot(db: Session, *, node: GroupTaskNode) -> dict[str, Any]:
    rows = list_nodes(db, run_id=int(node.run_id))
    rows_by_id = {int(row.id): row for row in rows}
    latest = rows_by_id.get(int(node.id), node)
    return _row_snapshot(latest, rows_by_id)


def _refresh_run_status(db: Session, *, run_id: int) -> GroupTaskRun:
    run = resolve_run(db, run_id=int(run_id))
    rows = list_nodes(db, run_id=int(run_id))
    if any(str(row.status) in {"blocked", "failed"} or str(row.manager_review_status) == "rework" for row in rows):
        run.status = "blocked"
    elif rows and all(str(row.status) == "completed" and str(row.manager_review_status) == "approved" for row in rows):
        run.status = "completed"
    else:
        run.status = "running"
    run.updated_at = datetime.now(timezone.utc)
    db.add(run)
    db.flush()
    return run


def _create_node_rows(db: Session, *, run: GroupTaskRun, nodes: list[dict]) -> list[GroupTaskNode]:
    validate_dag_nodes(nodes)
    by_key: dict[str, GroupTaskNode] = {}
    created: list[GroupTaskNode] = []
    for item in nodes:
        payload = _normalize_node_payload(item)
        parent_key = payload["parent_node_key"] or (payload["deps"][0] if payload["deps"] else None)
        parent_id = by_key[parent_key].id if parent_key and parent_key in by_key else None
        node = GroupTaskNode(
            group_id=int(run.group_id),
            run_id=int(run.id),
            parent_node_id=int(parent_id) if parent_id else None,
            node_key=payload["node_key"],
            title=payload["title"],
            detail=payload["detail"],
            role_required=payload["role_required"],
            status="pending",
            assignee_kind="unclaimed",
            assignee_member_id=None,
            attempt=0,
            input_json=json.dumps({"deps": payload["deps"]}, ensure_ascii=False),
            result_json="{}",
            error="",
            output_summary="",
            manager_review_status="pending",
            manager_review_note="",
            reviewed_at=None,
            reviewed_by_member_id=None,
        )
        db.add(node)
        db.flush()
        created.append(node)
        by_key[node.node_key] = node
    return created


def create_run(
    db: Session,
    *,
    group_id: int,
    creator_member_id: int,
    title: str,
    goal_text: str,
    nodes: list[dict] | None = None,
    trigger_message_id: int | None = None,
) -> GroupTaskRun:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    ensure_group_member(db, group_id=int(group_id), member_id=int(creator_member_id))
    run = GroupTaskRun(
        group_id=int(group_id),
        creator_member_id=int(creator_member_id),
        trigger_message_id=int(trigger_message_id) if trigger_message_id not in (None, "") else None,
        title=str(title or "").strip(),
        goal_text=str(goal_text or "").strip(),
        status="running",
    )
    db.add(run)
    db.flush()
    if nodes:
        _create_node_rows(db, run=run, nodes=nodes)
    _refresh_run_status(db, run_id=int(run.id))
    db.commit()
    db.refresh(run)
    if run.trigger_message_id is not None:
        try:
            from app.manager_runtime.assistant.state_store import bind_pending_run

            bind_pending_run(
                group_id=int(run.group_id),
                run_id=int(run.id),
                trigger_message_id=int(run.trigger_message_id),
            )
        except Exception:
            pass
    return run


def replace_run_nodes(db: Session, *, run_id: int, nodes: list[dict]) -> GroupTaskRun:
    run = resolve_run(db, run_id=int(run_id))
    validate_dag_nodes(nodes)
    for row in list_nodes(db, run_id=int(run_id)):
        db.delete(row)
    db.flush()
    _create_node_rows(db, run=run, nodes=nodes)
    _refresh_run_status(db, run_id=int(run_id))
    db.commit()
    db.refresh(run)
    return run


def _apply_deps_change(
    *,
    node: GroupTaskNode,
    nodes_by_key: dict[str, GroupTaskNode],
    deps: list[str],
    parent_node_key: str | None = None,
) -> None:
    effective_deps = [str(dep).strip() for dep in deps if str(dep).strip()]
    if parent_node_key and parent_node_key not in effective_deps:
        effective_deps = [parent_node_key, *effective_deps]
    effective_deps = [dep for dep in dict.fromkeys(effective_deps) if dep]
    for dep_key in effective_deps:
        if dep_key not in nodes_by_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Node '{node.node_key}' depends on unknown node_key '{dep_key}'",
            )
    parent_id = nodes_by_key[effective_deps[0]].id if effective_deps else None
    node.parent_node_id = int(parent_id) if parent_id else None
    node.input_json = json.dumps({"deps": effective_deps}, ensure_ascii=False)


def _snapshot_from_db(db: Session, *, run_id: int) -> list[dict[str, Any]]:
    rows = list_nodes(db, run_id=int(run_id))
    rows_by_id = {int(row.id): row for row in rows}
    return [_row_snapshot(row, rows_by_id) for row in rows]


def patch_dag(db: Session, *, run_id: int, ops: list[dict]) -> DagPatchResult:
    run = resolve_run(db, run_id=int(run_id))
    if not isinstance(ops, list) or not ops:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ops cannot be empty")

    current_rows = list_nodes(db, run_id=int(run_id))
    nodes_by_key: dict[str, GroupTaskNode] = {row.node_key: row for row in current_rows}
    created_node_keys: list[str] = []
    updated_node_keys: list[str] = []
    deleted_node_keys: list[str] = []

    try:
        for raw_op in ops:
            if not isinstance(raw_op, dict):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid op payload")
            op = str(raw_op.get("op") or "").strip()
            if op in {"add_node", "add_nodes"}:
                payload_nodes = [raw_op.get("node") or {}] if op == "add_node" else raw_op.get("nodes")
                if not isinstance(payload_nodes, list) or not payload_nodes:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="nodes cannot be empty")
                for item in payload_nodes:
                    payload = _normalize_node_payload(item or {})
                    if payload["node_key"] in nodes_by_key:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Node '{payload['node_key']}' already exists")
                    deps = list(payload["deps"])
                    if payload["parent_node_key"] and payload["parent_node_key"] not in deps:
                        deps = [payload["parent_node_key"], *deps]
                    deps = [dep for dep in dict.fromkeys(deps) if dep]
                    for dep_key in deps:
                        if dep_key not in nodes_by_key:
                            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Node '{payload['node_key']}' depends on unknown node_key '{dep_key}'")
                    parent_id = nodes_by_key[deps[0]].id if deps else None
                    node = GroupTaskNode(
                        group_id=int(run.group_id),
                        run_id=int(run.id),
                        parent_node_id=int(parent_id) if parent_id else None,
                        node_key=payload["node_key"],
                        title=payload["title"],
                        detail=payload["detail"],
                        role_required=payload["role_required"],
                        status="pending",
                        assignee_kind="unclaimed",
                        assignee_member_id=None,
                        attempt=0,
                        input_json=json.dumps({"deps": deps}, ensure_ascii=False),
                        result_json="{}",
                        error="",
                        output_summary="",
                        manager_review_status="pending",
                        manager_review_note="",
                        reviewed_at=None,
                        reviewed_by_member_id=None,
                    )
                    db.add(node)
                    db.flush()
                    nodes_by_key[node.node_key] = node
                    created_node_keys.append(node.node_key)
            elif op == "update_node":
                node_key = str(raw_op.get("node_key") or "").strip()
                if not node_key:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node_key is required")
                node = nodes_by_key.get(node_key)
                if not node:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_key}' not found")
                changes = _normalize_node_changes(raw_op.get("changes") or {})
                if changes["title"] is not None:
                    node.title = changes["title"]
                if changes["detail"] is not None:
                    node.detail = changes["detail"]
                if changes["role_required"] is not None:
                    node.role_required = changes["role_required"]
                if changes["deps"] is not None or changes["parent_node_key"] is not None:
                    _apply_deps_change(
                        node=node,
                        nodes_by_key=nodes_by_key,
                        deps=list(changes["deps"] or []),
                        parent_node_key=changes["parent_node_key"],
                    )
                db.add(node)
                db.flush()
                updated_node_keys.append(node.node_key)
            elif op in {"delete_node", "delete_nodes"}:
                node_keys = [raw_op.get("node_key")] if op == "delete_node" else raw_op.get("node_keys")
                if not isinstance(node_keys, list) or not node_keys:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node_keys cannot be empty")
                for key in node_keys:
                    node_key = str(key or "").strip()
                    if not node_key:
                        continue
                    node = nodes_by_key.pop(node_key, None)
                    if not node:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_key}' not found")
                    db.delete(node)
                    deleted_node_keys.append(node_key)
                db.flush()
            elif op == "replace_deps":
                node_key = str(raw_op.get("node_key") or "").strip()
                if not node_key:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node_key is required")
                node = nodes_by_key.get(node_key)
                if not node:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_key}' not found")
                deps = raw_op.get("deps")
                if not isinstance(deps, list):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="deps must be a list")
                _apply_deps_change(node=node, nodes_by_key=nodes_by_key, deps=[str(dep).strip() for dep in deps], parent_node_key=None)
                db.add(node)
                db.flush()
                updated_node_keys.append(node.node_key)
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported op '{op}'")

        snapshot = _snapshot_from_db(db, run_id=int(run_id))
        validate_dag_nodes([{"node_key": n["node_key"], "deps": n["deps"]} for n in snapshot])
        _refresh_run_status(db, run_id=int(run_id))
        db.commit()
        edge_count = sum(len(n["deps"]) for n in snapshot)
        return DagPatchResult(
            group_id=int(run.group_id),
            run_id=int(run.id),
            node_count=len(snapshot),
            edge_count=edge_count,
            created_node_keys=created_node_keys,
            updated_node_keys=updated_node_keys,
            deleted_node_keys=deleted_node_keys,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def update_node_status(
    db: Session,
    *,
    node_id: int,
    status_value: str,
    output_summary: str | None = None,
    error: str | None = None,
) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    node.status = str(status_value or "pending")
    if output_summary is not None:
        node.output_summary = output_summary.strip()
    if error is not None:
        node.error = error.strip()
    node.updated_at = datetime.now(timezone.utc)
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def claim_node(db: Session, *, node_id: int, member_id: int) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    member = ensure_group_member(db, group_id=int(node.group_id), member_id=int(member_id))
    deps = _deps_from_row(node)
    if deps:
        rows = list_nodes(db, run_id=int(node.run_id))
        status_by_key = {row.node_key: row.status for row in rows}
        review_by_key = {row.node_key: row.manager_review_status for row in rows}
        unmet = [dep for dep in deps if status_by_key.get(dep) != "completed" or review_by_key.get(dep) != "approved"]
        if unmet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dependencies not completed: {', '.join(unmet)}")
    node.assignee_member_id = int(member.id)
    node.assignee_kind = "user"
    node.status = "running"
    node.manager_review_status = "pending"
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def complete_node(db: Session, *, node_id: int, member_id: int, output_summary: str) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if not node.assignee_member_id:
        node.assignee_member_id = int(member_id)
    if int(node.assignee_member_id) != int(member_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assignee can complete this node")
    node.status = "completed"
    node.output_summary = str(output_summary or "").strip()
    node.result_json = json.dumps({"summary": node.output_summary, "status": "completed"}, ensure_ascii=False)
    node.error = ""
    node.manager_review_status = "pending"
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def assign_node_to_agent(db: Session, *, node_id: int, member_id: int) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    member = db.query(Member).filter(Member.id == int(member_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    ensure_group_member(db, group_id=int(node.group_id), member_id=int(member.id))
    node.assignee_member_id = int(member.id)
    node.assignee_kind = "agent"
    node.status = "running"
    node.manager_review_status = "pending"
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def mark_node_failed(db: Session, *, node_id: int, error: str) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    node.status = "failed"
    node.error = str(error or "").strip()
    node.manager_review_status = "pending"
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def requeue_node(db: Session, *, node_id: int, reason: str | None = None) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    node.status = "pending"
    node.assignee_kind = "unclaimed"
    node.assignee_member_id = None
    node.error = str(reason or "").strip()
    node.manager_review_status = "pending"
    node.manager_review_note = ""
    node.reviewed_at = None
    node.reviewed_by_member_id = None
    node.updated_at = datetime.now(timezone.utc)
    node.attempt = int(node.attempt or 0) + 1
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def review_node(
    db: Session,
    *,
    node_id: int,
    reviewer_member_id: int,
    manager_review_status: str,
    note: str = "",
) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    ensure_group_member(db, group_id=int(node.group_id), member_id=int(reviewer_member_id))
    review_status = str(manager_review_status or "").strip().lower()
    if review_status not in {"approved", "rework"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review status")
    node.manager_review_status = review_status
    node.manager_review_note = str(note or "").strip()
    node.reviewed_at = datetime.now(timezone.utc)
    node.reviewed_by_member_id = int(reviewer_member_id)
    if review_status == "rework":
        node.status = "blocked"
        node.error = node.manager_review_note
    elif review_status == "approved" and node.status == "blocked":
        node.status = "completed"
    db.add(node)
    _refresh_run_status(db, run_id=int(node.run_id))
    db.commit()
    db.refresh(node)
    return node


def block_role_branch(db: Session, *, run_id: int, role_required: str, reason: str) -> int:
    resolve_run(db, run_id=int(run_id))
    role = str(role_required or "").strip()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role_required is required")
    rows = (
        db.query(GroupTaskNode)
        .filter(GroupTaskNode.run_id == int(run_id), GroupTaskNode.role_required == role)
        .all()
    )
    for row in rows:
        row.status = "blocked"
        row.error = str(reason or "").strip()
        db.add(row)
    _refresh_run_status(db, run_id=int(run_id))
    db.commit()
    return len(rows)


def unblock_role_branch(db: Session, *, run_id: int, role_required: str, reason: str) -> int:
    resolve_run(db, run_id=int(run_id))
    role = str(role_required or "").strip()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role_required is required")
    rows = (
        db.query(GroupTaskNode)
        .filter(GroupTaskNode.run_id == int(run_id), GroupTaskNode.role_required == role, GroupTaskNode.status == "blocked")
        .all()
    )
    for row in rows:
        row.status = "pending"
        row.error = str(reason or "").strip()
        row.manager_review_status = "pending"
        db.add(row)
    _refresh_run_status(db, run_id=int(run_id))
    db.commit()
    return len(rows)


def list_run_events(db: Session, *, run_id: int) -> list[MessageEvent]:
    resolve_run(db, run_id=int(run_id))
    return (
        db.query(MessageEvent)
        .filter(MessageEvent.run_id == int(run_id))
        .order_by(MessageEvent.id.asc())
        .all()
    )
