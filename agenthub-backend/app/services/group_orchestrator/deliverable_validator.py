from __future__ import annotations

from pathlib import Path

from app.common.file_utils import normalize_rel_path, safe_resolve_under_root


def validate_deliverable_files(*, project_root: Path, deliverables: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Keep only deliverable file paths that actually exist under project_root.
    Return (filtered_deliverables, issues).
    """
    issues: list[str] = []
    out: list[dict] = []
    root = project_root.resolve()
    for d in deliverables or []:
        if not isinstance(d, dict):
            continue
        if str(d.get("type") or "") != "file":
            out.append(d)
            continue
        rel = str(d.get("value") or "").strip()
        if not rel:
            continue
        # Normalize and resolve under root; reject escape.
        try:
            rel_norm = normalize_rel_path(rel)
            target = safe_resolve_under_root(root, rel_norm)
        except Exception:
            issues.append(f"deliverable 文件路径非法或越界：{rel}")
            continue
        if not target.exists():
            issues.append(f"deliverable 文件不存在：{rel_norm}")
            continue
        out.append({"type": "file", "value": rel_norm})
    return out, issues

