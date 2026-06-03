from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.member import Member


def ensure_group_member(db: Session, *, group_id: int, member_id: int) -> Member:
    member = db.query(Member).filter(Member.id == int(member_id), Member.group_id == int(group_id)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member not in group")
    return member


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
