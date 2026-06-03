from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group_task_node import GroupTaskNode
from app.models.member import Member
from app.services.group_task.dag_service import get_node, list_nodes
from app.services.group_task.helpers import ensure_group_member


def _deps_from_node(node: GroupTaskNode) -> list[str]:
    try:
        payload = json.loads(node.input_json or "{}")
    except Exception:
        payload = {}
    deps = payload.get("deps") if isinstance(payload, dict) else []
    if not isinstance(deps, list):
        return []
    return [str(dep).strip() for dep in deps if str(dep).strip()]


def claim_node(db: Session, *, node_id: int, member_id: int) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    member = ensure_group_member(db, group_id=int(node.group_id), member_id=int(member_id))
    deps = _deps_from_node(node)
    if deps:
        rows = list_nodes(db, group_id=int(node.group_id))
        status_by_key = {row.node_key: row.status for row in rows}
        unmet = [dep for dep in deps if status_by_key.get(dep) != "completed"]
        if unmet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dependencies not completed: {', '.join(unmet)}",
            )
    node.assignee_member_id = int(member.id)
    node.assignee_kind = "user"
    node.status = "running"
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def complete_node(db: Session, *, node_id: int, member_id: int, output_summary: str) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if not node.assignee_member_id or int(node.assignee_member_id) != int(member_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assignee can complete this node")
    node.status = "completed"
    node.output_summary = str(output_summary or "").strip()
    node.result_json = json.dumps({"summary": node.output_summary, "status": "completed"}, ensure_ascii=False)
    node.error = ""
    db.add(node)
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
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def mark_node_failed(db: Session, *, node_id: int, error: str) -> GroupTaskNode:
    node = get_node(db, node_id=int(node_id))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    node.status = "failed"
    node.error = str(error or "").strip()
    db.add(node)
    db.commit()
    db.refresh(node)
    return node
