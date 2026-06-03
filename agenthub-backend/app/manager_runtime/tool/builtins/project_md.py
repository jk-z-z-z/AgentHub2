from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from agentscope.tool import ToolBase, ToolChunk

from app.common.file_utils import normalize_rel_path, safe_resolve_under_root, write_text
from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.services.storage_paths import project_dir


ALLOWED_MD_ROOTS: set[str] = {"knowledge", "runs"}
ALLOWED_MD_FILES: set[str] = {"MEMORY.md", "README.md"}


class ProjectMdTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self) -> None:
        self.name = "manager.project_md"
        self.description = "Project markdown file operations."
        self.input_schema = {
            "type": "object",
            "properties": {
                "op": {"type": "string"},
                "group_id": {"type": "integer"},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string"},
            },
            "required": ["op", "group_id", "path"],
            "additionalProperties": True,
        }

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

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        op = str(kwargs.get("op") or "").strip()
        group_id = int(kwargs.get("group_id"))
        path = str(kwargs.get("path") or "").strip()
        if not path:
            return build_error_chunk("path is required")
        target = self._resolve(group_id=group_id, path=path)

        if op == "read":
            if not target.exists() or not target.is_file():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            return build_tool_chunk(
                {
                    "path": target.relative_to(project_dir(int(group_id))).as_posix(),
                    "content": target.read_text(encoding="utf-8"),
                }
            )

        if op == "write":
            content = str(kwargs.get("content") or "")
            mode = str(kwargs.get("mode") or "overwrite")
            target.parent.mkdir(parents=True, exist_ok=True)
            write_text(target, content, mode)
            return build_tool_chunk(
                {
                    "path": target.relative_to(project_dir(int(group_id))).as_posix(),
                    "written": True,
                    "mode": mode,
                }
            )

        if op == "list":
            root = project_dir(int(group_id)).resolve()
            base = self._resolve(group_id=group_id, path=path)
            if base.is_file():
                base = base.parent
            if not base.exists():
                return build_tool_chunk({"entries": []})
            entries = []
            for p in sorted(base.rglob("*.md")):
                try:
                    rel = p.relative_to(root).as_posix()
                except Exception:
                    continue
                entries.append({"path": rel, "size": p.stat().st_size})
                if len(entries) >= 200:
                    break
            return build_tool_chunk({"entries": entries})

        return build_error_chunk("Unsupported op")
