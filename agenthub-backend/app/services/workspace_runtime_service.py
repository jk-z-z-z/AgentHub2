from __future__ import annotations

import hashlib
import json
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.member import Member
from app.models.workspace import Workspace
from app.services.project_code_service import get_project_code_root
from app.services.storage_paths import workspace_meta_dir, workspace_snapshots_dir


def build_tenant_id(*, user_id: int) -> str:
    return f"user:{int(user_id)}"


@dataclass
class WorkspaceSnapshot:
    snapshot_id: str
    snapshot_path: str
    digest: str
    file_count: int
    created_at: str
    source_path: str


class WorkspaceBackend(ABC):
    backend_type = "unknown"

    @abstractmethod
    def resolve_source_root(self, workspace: Workspace) -> Path:
        raise NotImplementedError

    @abstractmethod
    def create_snapshot(self, workspace: Workspace, *, label: str | None = None) -> WorkspaceSnapshot:
        raise NotImplementedError


def _hash_tree(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if path.is_dir():
            digest.update(b"dir")
            continue
        if path.is_file():
            count += 1
            digest.update(str(path.stat().st_size).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest(), count


class LocalWorkspaceBackend(WorkspaceBackend):
    backend_type = "local_fs"

    def resolve_source_root(self, workspace: Workspace) -> Path:
        root = Path(str(workspace.source_path or "")).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def create_snapshot(self, workspace: Workspace, *, label: str | None = None) -> WorkspaceSnapshot:
        source_root = self.resolve_source_root(workspace)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = hashlib.sha1(f"{workspace.id}:{label or ''}:{stamp}".encode("utf-8")).hexdigest()[:10]
        snapshot_id = f"{stamp}-{suffix}"
        target = workspace_snapshots_dir(int(workspace.id)) / snapshot_id
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source_root, target, dirs_exist_ok=False)
        digest, count = _hash_tree(target)
        return WorkspaceSnapshot(
            snapshot_id=snapshot_id,
            snapshot_path=target.as_posix(),
            digest=digest,
            file_count=count,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_path=source_root.as_posix(),
        )


def _workspace_backend_for(workspace: Workspace) -> WorkspaceBackend:
    if str(workspace.backend_type) == "local_fs":
        return LocalWorkspaceBackend()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported workspace backend")


def _workspace_metadata(workspace: Workspace) -> dict:
    try:
        raw = json.loads(workspace.metadata_json or "{}")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def get_workspace_for_project(db: Session, *, project_id: int) -> Workspace | None:
    return db.query(Workspace).filter(Workspace.project_id == int(project_id)).first()


def ensure_workspace_for_project_id(db: Session, *, project_id: int) -> Workspace:
    existing = get_workspace_for_project(db, project_id=int(project_id))
    if existing:
        return existing
    group = db.query(Group).filter(Group.id == int(project_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project group not found")
    return ensure_workspace_for_group(db, group=group)


def get_workspace_by_id(db: Session, *, workspace_id: int) -> Workspace | None:
    return db.query(Workspace).filter(Workspace.id == int(workspace_id)).first()


def ensure_workspace_for_group(db: Session, *, group: Group) -> Workspace:
    if str(group.type) != "project":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only project groups have workspaces")
    existing = get_workspace_for_project(db, project_id=int(group.id))
    source_root = get_project_code_root(int(group.id)).as_posix()
    if existing:
        existing.source_path = source_root
        existing.name = f"{group.name} workspace"
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    row = Workspace(
        creator_user_id=int(group.creator_user_id),
        tenant_id=build_tenant_id(user_id=int(group.creator_user_id)),
        project_id=int(group.id),
        name=f"{group.name} workspace",
        backend_type="local_fs",
        source_path=source_root,
        metadata_json=json.dumps({"source_kind": "project_shared_code"}, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    workspace_meta_dir(int(row.id)).mkdir(parents=True, exist_ok=True)
    return row


def assert_workspace_access(db: Session, *, workspace_id: int, user_id: int) -> Workspace:
    workspace = get_workspace_by_id(db, workspace_id=int(workspace_id))
    if not workspace or int(workspace.is_active or 0) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    member = (
        db.query(Member)
        .filter(
            Member.group_id == int(workspace.project_id),
            Member.kind == "user",
            Member.user_ref == str(int(user_id)),
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return workspace


def create_workspace_snapshot_record(
    db: Session,
    *,
    workspace: Workspace,
    label: str | None = None,
) -> WorkspaceSnapshot:
    backend = _workspace_backend_for(workspace)
    snapshot = backend.create_snapshot(workspace, label=label)
    workspace.last_snapshot_id = snapshot.snapshot_id
    workspace.last_snapshot_digest = snapshot.digest
    workspace.last_snapshot_path = snapshot.snapshot_path
    workspace.last_snapshot_file_count = int(snapshot.file_count)
    meta = _workspace_metadata(workspace)
    meta["last_snapshot_created_at"] = snapshot.created_at
    workspace.metadata_json = json.dumps(meta, ensure_ascii=False)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return snapshot


def create_workspace_snapshot_for_user(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    label: str | None = None,
) -> tuple[Workspace, WorkspaceSnapshot]:
    workspace = assert_workspace_access(db, workspace_id=int(workspace_id), user_id=int(user_id))
    snapshot = create_workspace_snapshot_record(db, workspace=workspace, label=label)
    return workspace, snapshot


def build_execution_context(
    *,
    workspace: Workspace,
    user_id: int,
    sandbox_id: str | None,
) -> dict[str, object]:
    return {
        "tenant_id": str(workspace.tenant_id),
        "project_id": int(workspace.project_id),
        "user_id": int(user_id),
        "workspace_id": int(workspace.id),
        "sandbox_id": sandbox_id,
    }
