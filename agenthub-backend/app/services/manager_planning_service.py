from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.group_task.dag_service import list_nodes, patch_nodes
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


async def manager_tool_apply_plan(
    db: Session,
    *,
    group_id: int,
    creator_member_id: int,
    plan: dict,
) -> dict:
    nodes = list(plan.get("nodes") or [])
    current = list_nodes(db, group_id=int(group_id))
    action = "updated" if current else "created"
    patch_nodes(db, group_id=int(group_id), creator_member_id=int(creator_member_id), nodes=nodes)
    return {"action": action, "node_count": len(nodes)}
