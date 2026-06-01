from __future__ import annotations

from pathlib import Path

from app.services.storage_init_service import ensure_agent_space
from app.services.storage_paths import agent_dir


ALLOWED_AGENT_TEXT_FILES: set[str] = {
    "SOUL.md",
    "PROFILE.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
    "tools.json",
    "skills.json",
    "profile.enabled_files.json",
}
ALLOWED_AGENT_DIRS: set[str] = {"skills", "knowledge", "mcps"}

# Guardrails to avoid accidental huge directory listings / writes in dev.
MAX_LISTED_ENTRIES = 2000
MAX_DEPTH = 8


def _safe_join(base: Path, rel_path: str) -> Path:
    rel = rel_path.strip().lstrip("/").replace("\\", "/")
    if not rel or rel in {".", ".."}:
        raise ValueError("Invalid path")
    if "/.." in f"/{rel}":
        raise ValueError("Invalid path")
    full = (base / rel).resolve()
    base_resolved = base.resolve()
    if base_resolved not in full.parents and full != base_resolved:
        raise ValueError("Path escapes base")
    return full


def _validate_rel_path(rel_path: str) -> str:
    rel = (rel_path or "").strip().lstrip("/").replace("\\", "/")
    if not rel:
        raise ValueError("Invalid path")
    if rel in {".", ".."}:
        raise ValueError("Invalid path")
    if "/.." in f"/{rel}":
        raise ValueError("Invalid path")
    return rel


def _iter_entries(root: Path, top_dir: str) -> list[dict]:
    """
    Recursively list entries under {root}/{top_dir}.
    We include directories (with trailing "/") and files.
    """
    base = root / top_dir
    base.mkdir(parents=True, exist_ok=True)

    out: list[dict] = []
    # Depth-first traversal with explicit stack to keep control.
    stack: list[tuple[Path, int]] = [(base, 0)]

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


def list_agent_fs(agent_id: int) -> list[dict]:
    ensure_agent_space(agent_id)
    root = agent_dir(agent_id)

    out: list[dict] = []
    for fname in sorted(ALLOWED_AGENT_TEXT_FILES):
        p = root / fname
        out.append({"path": fname, "is_dir": False, "size": p.stat().st_size if p.exists() else 0})
    for dname in sorted(ALLOWED_AGENT_DIRS):
        out.append({"path": f"{dname}/", "is_dir": True, "size": 0})
        out.extend(_iter_entries(root, dname))
    return out


def read_agent_text_file(agent_id: int, rel_path: str) -> str:
    ensure_agent_space(agent_id)
    root = agent_dir(agent_id)
    rel_path = _validate_rel_path(rel_path)
    if rel_path in ALLOWED_AGENT_TEXT_FILES:
        p = root / rel_path
        return p.read_text(encoding="utf-8") if p.exists() else ""

    parts = rel_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Unsupported path")
    top, name = parts
    if top not in ALLOWED_AGENT_DIRS:
        raise ValueError("Unsupported path")
    if not name:
        raise ValueError("Unsupported path")
    p = _safe_join(root, f"{top}/{name}")
    if not p.exists() or not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def write_agent_text_file(agent_id: int, rel_path: str, content: str) -> None:
    ensure_agent_space(agent_id)
    root = agent_dir(agent_id)
    rel_path = _validate_rel_path(rel_path)
    if rel_path in ALLOWED_AGENT_TEXT_FILES:
        p = root / rel_path
        p.write_text(content or "", encoding="utf-8")
        return

    parts = rel_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Unsupported path")
    top, name = parts
    if top not in ALLOWED_AGENT_DIRS:
        raise ValueError("Unsupported path")
    if not name:
        raise ValueError("Unsupported path")
    p = _safe_join(root, f"{top}/{name}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content or "", encoding="utf-8")


def delete_agent_file(agent_id: int, rel_path: str) -> None:
    ensure_agent_space(agent_id)
    root = agent_dir(agent_id)
    rel_path = _validate_rel_path(rel_path)
    if rel_path in ALLOWED_AGENT_TEXT_FILES:
        raise ValueError("Cannot delete core agent file")

    parts = rel_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Unsupported path")
    top, name = parts
    if top not in ALLOWED_AGENT_DIRS:
        raise ValueError("Unsupported path")
    if not name:
        raise ValueError("Unsupported path")
    p = _safe_join(root, f"{top}/{name}")
    if p.exists() and p.is_file():
        p.unlink()
