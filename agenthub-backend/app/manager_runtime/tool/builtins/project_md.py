from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

from app.common.file_utils import normalize_rel_path, safe_resolve_under_root, write_text
from app.manager_runtime.tool.base import ManagerTool, ToolCallResult
from app.services.storage_paths import project_dir


ALLOWED_MD_ROOTS: set[str] = {"knowledge", "runs"}
ALLOWED_MD_FILES: set[str] = {"MEMORY.md", "README.md"}


class ProjectMdTool(ManagerTool):
    code = "manager.project_md"

    def _resolve(self, *, group_id: int, path: str) -> Path:
        root = project_dir(int(group_id)).resolve()
        rel = normalize_rel_path(path)
        if rel in ALLOWED_MD_FILES:
            return (root / rel).resolve()
        top = rel.split("/", 1)[0]
        if top not in ALLOWED_MD_ROOTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"path must be one of {sorted(ALLOWED_MD_FILES)} or under {sorted(ALLOWED_MD_ROOTS)}",
            )
        target = safe_resolve_under_root(root, rel)
        if target.suffix.lower() != ".md":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only .md files are allowed")
        return target

    async def __call__(self, **kwargs) -> ToolCallResult:
        op = str(kwargs.get("op") or "").strip()
        group_id = int(kwargs.get("group_id"))
        path = str(kwargs.get("path") or "").strip()
        if not path:
            return ToolCallResult(ok=False, result={}, error="path is required")
        target = self._resolve(group_id=group_id, path=path)

        if op == "read":
            if not target.exists() or not target.is_file():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            return ToolCallResult(
                ok=True,
                result={"path": target.relative_to(project_dir(int(group_id))).as_posix(), "content": target.read_text(encoding="utf-8")},
            )

        if op == "write":
            content = str(kwargs.get("content") or "")
            mode = str(kwargs.get("mode") or "overwrite")
            target.parent.mkdir(parents=True, exist_ok=True)
            write_text(target, content, mode)
            return ToolCallResult(
                ok=True,
                result={"path": target.relative_to(project_dir(int(group_id))).as_posix(), "written": True, "mode": mode},
            )

        if op == "list":
            root = project_dir(int(group_id)).resolve()
            base = self._resolve(group_id=group_id, path=path)
            if base.is_file():
                base = base.parent
            if not base.exists():
                return ToolCallResult(ok=True, result={"entries": []})
            entries = []
            for p in sorted(base.rglob("*.md")):
                try:
                    rel = p.relative_to(root).as_posix()
                except Exception:
                    continue
                entries.append({"path": rel, "size": p.stat().st_size})
                if len(entries) >= 200:
                    break
            return ToolCallResult(ok=True, result={"entries": entries})

        return ToolCallResult(ok=False, result={}, error="Unsupported op")
