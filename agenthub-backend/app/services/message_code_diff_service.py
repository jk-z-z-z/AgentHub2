from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.event_runtime.facade import create_message_event, list_message_events
from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.schemas.message_code_diff import (
    MessageCodeDiffFileOut,
    MessageCodeDiffOut,
    MessageCodeDiffSummaryOut,
)
from app.services.project_code_service import get_project_code_root
from app.services.workspace_runtime_service import ensure_workspace_for_project_id


INITIAL_COMMIT_MESSAGE = "chore(agenthub): initialize project code repository"
PATCH_CHAR_LIMIT = 24000


@dataclass
class CodeDiffFile:
    path: str
    change_type: str
    old_path: str | None = None
    additions: int = 0
    deletions: int = 0
    patch: str | None = None
    patch_truncated: bool = False


@dataclass
class CodeDiffSummary:
    workspace_id: int
    group_id: int
    message_id: int
    repo_initialized: bool
    before_commit: str
    after_commit: str | None
    has_code_changes: bool
    changed_files: list[str]
    files_added: int
    files_modified: int
    files_deleted: int
    insertions: int
    deletions: int
    diff_preview_available: bool


@dataclass
class CodeDiffResult:
    status: str
    summary: CodeDiffSummary | None = None
    files: list[CodeDiffFile] | None = None
    error: str | None = None


def _run_git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "git command failed").strip())
    return completed


def _repo_exists(repo_root: Path) -> bool:
    return (repo_root / ".git").exists()


def ensure_project_code_repo(group_id: int) -> tuple[Path, bool]:
    repo_root = get_project_code_root(int(group_id))
    initialized = False
    if not _repo_exists(repo_root):
        _run_git(repo_root, "init")
        _run_git(repo_root, "config", "user.name", "AgentHub")
        _run_git(repo_root, "config", "user.email", "agenthub@local")
        _run_git(repo_root, "add", "-A")
        _run_git(repo_root, "commit", "--allow-empty", "-m", INITIAL_COMMIT_MESSAGE)
        initialized = True
    else:
        # Keep local identity configured even if repo pre-existed.
        _run_git(repo_root, "config", "user.name", "AgentHub")
        _run_git(repo_root, "config", "user.email", "agenthub@local")
    return repo_root, initialized


def get_head_commit(repo_root: Path) -> str:
    return _run_git(repo_root, "rev-parse", "HEAD").stdout.strip()


def has_working_tree_changes(repo_root: Path) -> bool:
    result = _run_git(repo_root, "status", "--porcelain", check=False)
    return bool((result.stdout or "").strip())


def _parse_numstat(before_commit: str, after_commit: str, repo_root: Path) -> tuple[dict[str, tuple[int, int]], int, int]:
    stats: dict[str, tuple[int, int]] = {}
    total_additions = 0
    total_deletions = 0
    raw = _run_git(repo_root, "diff", "--numstat", before_commit, after_commit).stdout
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add_raw, del_raw, path = parts[0], parts[1], parts[2]
        additions = 0 if add_raw == "-" else int(add_raw or 0)
        deletions = 0 if del_raw == "-" else int(del_raw or 0)
        stats[path] = (additions, deletions)
        total_additions += additions
        total_deletions += deletions
    return stats, total_additions, total_deletions


def _parse_name_status(before_commit: str, after_commit: str, repo_root: Path) -> list[tuple[str, str | None, str]]:
    rows: list[tuple[str, str | None, str]] = []
    raw = _run_git(repo_root, "diff", "--name-status", before_commit, after_commit).stdout
    for line in raw.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status_code = parts[0]
        if status_code.startswith("R") and len(parts) >= 3:
            rows.append(("renamed", parts[1], parts[2]))
        elif status_code.startswith("A") and len(parts) >= 2:
            rows.append(("added", None, parts[1]))
        elif status_code.startswith("D") and len(parts) >= 2:
            rows.append(("deleted", None, parts[1]))
        elif len(parts) >= 2:
            rows.append(("modified", None, parts[1]))
    return rows


def _is_binary_patch(patch_text: str) -> bool:
    lowered = patch_text.lower()
    return "binary files" in lowered or "git binary patch" in lowered


def _file_patch(repo_root: Path, before_commit: str, after_commit: str, path: str, old_path: str | None = None) -> tuple[str | None, bool]:
    args = ["diff", "--unified=3", before_commit, after_commit, "--"]
    if old_path:
        args.extend([old_path, path])
    else:
        args.append(path)
    patch = _run_git(repo_root, *args).stdout
    if not patch.strip():
        return None, False
    if _is_binary_patch(patch):
        return None, False
    if len(patch) > PATCH_CHAR_LIMIT:
        return patch[:PATCH_CHAR_LIMIT].rstrip() + "\n\n... diff truncated ...\n", True
    return patch, False


def build_message_diff_result(
    *,
    workspace_id: int,
    group_id: int,
    message_id: int,
    applied_files: list[str],
) -> CodeDiffResult:
    repo_root, repo_initialized = ensure_project_code_repo(int(group_id))
    before_commit = get_head_commit(repo_root)
    if not applied_files:
        return CodeDiffResult(
            status="no_changes",
            summary=CodeDiffSummary(
                workspace_id=int(workspace_id),
                group_id=int(group_id),
                message_id=int(message_id),
                repo_initialized=repo_initialized,
                before_commit=before_commit,
                after_commit=None,
                has_code_changes=False,
                changed_files=[],
                files_added=0,
                files_modified=0,
                files_deleted=0,
                insertions=0,
                deletions=0,
                diff_preview_available=False,
            ),
            files=[],
        )
    if not has_working_tree_changes(repo_root):
        return CodeDiffResult(
            status="no_changes",
            summary=CodeDiffSummary(
                workspace_id=int(workspace_id),
                group_id=int(group_id),
                message_id=int(message_id),
                repo_initialized=repo_initialized,
                before_commit=before_commit,
                after_commit=None,
                has_code_changes=False,
                changed_files=[],
                files_added=0,
                files_modified=0,
                files_deleted=0,
                insertions=0,
                deletions=0,
                diff_preview_available=False,
            ),
            files=[],
        )
    _run_git(repo_root, "add", "-A")
    _run_git(repo_root, "commit", "-m", f"chore(agenthub): message {int(message_id)} code update")
    after_commit = get_head_commit(repo_root)
    name_status = _parse_name_status(before_commit, after_commit, repo_root)
    numstats, total_additions, total_deletions = _parse_numstat(before_commit, after_commit, repo_root)
    files: list[CodeDiffFile] = []
    files_added = 0
    files_modified = 0
    files_deleted = 0
    changed_files: list[str] = []
    for change_type, old_path, path in name_status:
        additions, deletions = numstats.get(path, numstats.get(old_path or "", (0, 0)))
        patch, patch_truncated = _file_patch(repo_root, before_commit, after_commit, path, old_path=old_path)
        files.append(
            CodeDiffFile(
                path=path,
                change_type=change_type,
                old_path=old_path,
                additions=additions,
                deletions=deletions,
                patch=patch,
                patch_truncated=patch_truncated,
            )
        )
        changed_files.append(path)
        if change_type == "added":
            files_added += 1
        elif change_type == "deleted":
            files_deleted += 1
        else:
            files_modified += 1
    return CodeDiffResult(
        status="ready",
        summary=CodeDiffSummary(
            workspace_id=int(workspace_id),
            group_id=int(group_id),
            message_id=int(message_id),
            repo_initialized=repo_initialized,
            before_commit=before_commit,
            after_commit=after_commit,
            has_code_changes=bool(files),
            changed_files=changed_files,
            files_added=files_added,
            files_modified=files_modified,
            files_deleted=files_deleted,
            insertions=total_additions,
            deletions=total_deletions,
            diff_preview_available=bool(files),
        ),
        files=files,
    )


def _summary_payload(summary: CodeDiffSummary, *, error: str | None = None) -> dict:
    payload = {
        "workspace_id": int(summary.workspace_id),
        "group_id": int(summary.group_id),
        "message_id": int(summary.message_id),
        "repo_initialized": bool(summary.repo_initialized),
        "before_commit": summary.before_commit,
        "after_commit": summary.after_commit,
        "has_code_changes": bool(summary.has_code_changes),
        "changed_files": list(summary.changed_files),
        "files_added": int(summary.files_added),
        "files_modified": int(summary.files_modified),
        "files_deleted": int(summary.files_deleted),
        "insertions": int(summary.insertions),
        "deletions": int(summary.deletions),
        "diff_preview_available": bool(summary.diff_preview_available),
    }
    if error:
        payload["error"] = str(error)
    return payload


def create_code_diff_event(
    db: Session,
    *,
    user_message_id: int,
    result: CodeDiffResult,
) -> None:
    if result.summary is not None:
        payload = _summary_payload(result.summary, error=result.error)
    else:
        payload = {"message_id": int(user_message_id), "error": str(result.error or "diff unavailable")}
    create_message_event(
        db,
        message_id=int(user_message_id),
        event_type="code.diff.failed" if result.status == "failed" else "code.diff.ready",
        payload=payload,
        status="failed" if result.status == "failed" else "done",
    )


def capture_code_diff_for_message(
    db: Session,
    *,
    group_id: int,
    user_message_id: int,
    applied_files: list[str],
) -> CodeDiffResult:
    try:
        workspace = ensure_workspace_for_project_id(db, project_id=int(group_id))
        result = build_message_diff_result(
            workspace_id=int(workspace.id),
            group_id=int(group_id),
            message_id=int(user_message_id),
            applied_files=applied_files,
        )
        create_code_diff_event(db, user_message_id=int(user_message_id), result=result)
        return result
    except Exception as exc:
        failed = CodeDiffResult(status="failed", summary=None, files=[], error=str(exc))
        create_code_diff_event(db, user_message_id=int(user_message_id), result=failed)
        return failed


def _decode_payload(payload_json: str) -> dict:
    try:
        value = json.loads(payload_json or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _is_message_visible_to_user(db: Session, *, message: Message, user_id: int) -> bool:
    member = (
        db.query(Member)
        .filter(
            Member.group_id == int(message.group_id),
            Member.kind == "user",
            Member.user_ref == str(int(user_id)),
        )
        .first()
    )
    return member is not None


def _pick_diff_event(db: Session, *, message_id: int):
    events = list_message_events(db, message_id=int(message_id))
    latest_ready = None
    latest_failed = None
    for event in events:
        if str(event.event_type) == "code.diff.ready":
            latest_ready = event
        elif str(event.event_type) == "code.diff.failed":
            latest_failed = event
    return latest_ready or latest_failed


def get_message_code_diff(db: Session, *, message_id: int, user_id: int) -> MessageCodeDiffOut:
    message = db.query(Message).filter(Message.id == int(message_id)).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if not _is_message_visible_to_user(db, message=message, user_id=int(user_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    group = db.query(Group).filter(Group.id == int(message.group_id)).first()
    if not group or str(group.type) != "project":
        return MessageCodeDiffOut(status="unavailable", summary=None, files=[], error="Message does not belong to a project group")
    event = _pick_diff_event(db, message_id=int(message_id))
    if not event:
        return MessageCodeDiffOut(status="unavailable", summary=None, files=[], error=None)
    payload = _decode_payload(str(event.payload_json or "{}"))
    if str(event.event_type) == "code.diff.failed":
        return MessageCodeDiffOut(status="failed", summary=None, files=[], error=str(payload.get("error") or "diff unavailable"))
    before_commit = str(payload.get("before_commit") or "")
    after_commit = str(payload.get("after_commit") or "")
    summary = MessageCodeDiffSummaryOut(
        message_id=int(payload.get("message_id") or message_id),
        workspace_id=int(payload.get("workspace_id") or 0) or None,
        group_id=int(payload.get("group_id") or message.group_id),
        before_commit=before_commit or None,
        after_commit=after_commit or None,
        changed_file_count=len(payload.get("changed_files") or []),
        insertions=int(payload.get("insertions") or 0),
        deletions=int(payload.get("deletions") or 0),
        has_code_changes=bool(payload.get("has_code_changes")),
        repo_initialized=bool(payload.get("repo_initialized")),
        diff_preview_available=bool(payload.get("diff_preview_available")),
    )
    if not summary.after_commit or not summary.has_code_changes:
        return MessageCodeDiffOut(status="no_changes", summary=summary, files=[], error=None)
    repo_root, _ = ensure_project_code_repo(int(message.group_id))
    files: list[MessageCodeDiffFileOut] = []
    for item in _parse_name_status(before_commit, after_commit, repo_root):
        change_type, old_path, path = item
        numstats, _, _ = _parse_numstat(before_commit, after_commit, repo_root)
        additions, deletions = numstats.get(path, numstats.get(old_path or "", (0, 0)))
        patch, patch_truncated = _file_patch(repo_root, before_commit, after_commit, path, old_path=old_path)
        files.append(
            MessageCodeDiffFileOut(
                path=path,
                change_type=change_type,
                old_path=old_path,
                additions=additions,
                deletions=deletions,
                patch=patch,
                patch_truncated=patch_truncated,
            )
        )
    return MessageCodeDiffOut(status="ready", summary=summary, files=files, error=None)
