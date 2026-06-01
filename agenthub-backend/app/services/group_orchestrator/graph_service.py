from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.group_task_graph import GroupTaskGraph
from app.models.group_task_node import GroupTaskNode


def _build_edges_from_deps(nodes: list[GroupTaskNode]) -> list[dict]:
    edges: list[dict] = []
    by_key = {n.node_key: n for n in nodes}
    for n in nodes:
        try:
            deps = json.loads(n.deps_json or "[]")
        except Exception:
            deps = []
        for d in deps:
            if d in by_key:
                edges.append({"from": d, "to": n.node_key, "type": "hard", "condition": "on_success"})
    return edges


def build_graph_snapshot(*, run_id: int, nodes: list[GroupTaskNode], goal: str | None = None, version: int = 1) -> dict:
    return {
        "run_id": int(run_id),
        "version": int(version),
        "goal": str(goal or ""),
        "nodes": [
            {
                "node_id": int(n.id),
                "node_key": n.node_key,
                "title": n.title,
                "assigned_agent_member_id": int(n.assignee_member_id) if n.assignee_member_id else None,
                "assignee_kind": n.assignee_kind,
                "status": n.status,
                "attempt": int(getattr(n, "attempt", 0) or 0),
                "receipt_message_id": int(getattr(n, "receipt_message_id", 0) or 0) if getattr(n, "receipt_message_id", None) else None,
            }
            for n in nodes
        ],
        "edges": _build_edges_from_deps(nodes),
    }


def upsert_graph_snapshot(db: Session, *, run_id: int, version: int, snapshot: dict) -> GroupTaskGraph:
    row = (
        db.query(GroupTaskGraph)
        .filter(GroupTaskGraph.run_id == int(run_id), GroupTaskGraph.version == int(version))
        .first()
    )
    if not row:
        row = GroupTaskGraph(run_id=int(run_id), version=int(version), snapshot_json="{}")
    row.snapshot_json = json.dumps(snapshot or {}, ensure_ascii=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_graph_snapshot(db: Session, *, run_id: int) -> GroupTaskGraph | None:
    return (
        db.query(GroupTaskGraph)
        .filter(GroupTaskGraph.run_id == int(run_id))
        .order_by(GroupTaskGraph.version.desc())
        .first()
    )

