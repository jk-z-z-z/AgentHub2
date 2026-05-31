from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group_assistant_config import GroupAssistantConfig
from app.models.group_task_node import GroupTaskNode
from app.models.group_task_run import GroupTaskRun
from app.models.member import Member
from app.services.storage_paths import project_dir


def runtime_dir_for_run(group_id: int, run_id: int) -> Path:
    return project_dir(int(group_id)) / "runs" / str(run_id)


def ensure_group_member(db: Session, *, group_id: int, member_id: int) -> Member:
    member = db.query(Member).filter(Member.id == int(member_id), Member.group_id == int(group_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member not in group")
    return member


def assistant_is_enabled(db: Session, *, group_id: int) -> bool:
    cfg = db.query(GroupAssistantConfig).filter(GroupAssistantConfig.group_id == int(group_id)).first()
    return bool(cfg and int(cfg.enabled) == 1)


def write_run_files(run: GroupTaskRun, nodes: list[GroupTaskNode]) -> None:
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
        deps = [str(d).strip() for d in (item.get("deps") or []) if str(d).strip()]
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
