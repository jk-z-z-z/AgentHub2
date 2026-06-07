from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.services.storage_init_service import ensure_project_space
from app.services.storage_paths import project_dir


MAX_LISTED_ENTRIES = 3000
MAX_DEPTH = 12


def get_project_code_root(group_id: int) -> Path:
    ensure_project_space(group_id)
    root = project_dir(group_id) / "shared" / "code"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def ensure_user_can_access_project_code(db: Session, *, group_id: int, user_id: int) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if str(group.type) != "project":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only project groups have project code space")

    member = (
        db.query(Member)
        .filter(Member.group_id == group_id, Member.kind == "user", Member.user_ref == str(user_id))
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return group


def normalize_project_rel_path(rel_path: str) -> str:
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if rel in {"", ".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if "/.." in f"/{rel}":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return rel


def safe_project_code_path(group_id: int, rel_path: str) -> Path:
    root = get_project_code_root(group_id)
    rel = normalize_project_rel_path(rel_path)
    full = (root / rel).resolve()
    if root not in full.parents and full != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path escapes project code root")
    return full


def list_project_code_fs(group_id: int) -> list[dict]:
    root = get_project_code_root(group_id)
    out: list[dict] = []
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        cur, depth = stack.pop()
        if depth > MAX_DEPTH:
            continue
        try:
            children = sorted(cur.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except FileNotFoundError:
            continue

        for child in children:
            if len(out) >= MAX_LISTED_ENTRIES:
                return out
            rel = child.relative_to(root).as_posix()
            if child.is_dir():
                out.append({"path": f"{rel}/", "is_dir": True, "size": 0})
                stack.append((child, depth + 1))
            elif child.is_file():
                out.append({"path": rel, "is_dir": False, "size": child.stat().st_size})
    return out


def read_project_code_file(group_id: int, rel_path: str) -> str:
    path = safe_project_code_path(group_id, rel_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return path.read_text(encoding="utf-8")


def write_project_code_file(group_id: int, rel_path: str, content: str) -> dict[str, str]:
    path = safe_project_code_path(group_id, rel_path)
    if path.exists() and path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot overwrite a directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content), encoding="utf-8")
    return {
        "path": normalize_project_rel_path(rel_path),
        "content": str(content),
    }
