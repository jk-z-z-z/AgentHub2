from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status


def normalize_rel_path(rel_path: str) -> str:
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not rel or rel in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if "/.." in f"/{rel}":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return rel


def normalize_rel_dir(rel_path: str, *, allow_root: bool = False) -> str:
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if rel in {"", "."}:
        if allow_root:
            return "."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if rel == ".." or "/.." in f"/{rel}":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return rel.rstrip("/")


def safe_resolve_under_root(root: Path, rel_path: str) -> Path:
    rel = normalize_rel_path(rel_path)
    full = (root / rel).resolve()
    if root not in full.parents and full != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path escapes root")
    return full


def list_dir_entries(base_root: Path, target: Path) -> list[dict]:
    entries = []
    for child in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        rel = child.relative_to(base_root).as_posix()
        entries.append(
            {
                "name": child.name,
                "path": f"{rel}/" if child.is_dir() else rel,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else 0,
            }
        )
    return entries


def write_text(path: Path, content: str, mode: str) -> None:
    write_mode = str(mode or "overwrite").lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if write_mode == "append":
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(f"{existing}{content}", encoding="utf-8")
        return
    if write_mode != "overwrite":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be overwrite or append")
    path.write_text(content, encoding="utf-8")
