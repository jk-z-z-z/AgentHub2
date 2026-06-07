from __future__ import annotations

from app.schemas.common import ORMBaseModel


class MessageCodeDiffFileOut(ORMBaseModel):
    path: str
    change_type: str
    old_path: str | None = None
    additions: int = 0
    deletions: int = 0
    patch: str | None = None
    patch_truncated: bool = False


class MessageCodeDiffSummaryOut(ORMBaseModel):
    message_id: int
    workspace_id: int | None = None
    group_id: int
    before_commit: str | None = None
    after_commit: str | None = None
    changed_file_count: int = 0
    insertions: int = 0
    deletions: int = 0
    has_code_changes: bool = False
    repo_initialized: bool = False
    diff_preview_available: bool = False


class MessageCodeDiffOut(ORMBaseModel):
    status: str
    summary: MessageCodeDiffSummaryOut | None = None
    files: list[MessageCodeDiffFileOut]
    error: str | None = None
