from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class WorkspaceSnapshotCreateRequest(ORMBaseModel):
    label: str | None = Field(default=None, max_length=120)


class WorkspaceOut(ORMBaseModel):
    id: int
    project_id: int
    tenant_id: str
    name: str
    backend_type: str
    source_path: str
    last_snapshot_id: str | None
    last_snapshot_digest: str | None
    last_snapshot_file_count: int
    created_at: datetime
    updated_at: datetime


class WorkspaceSnapshotOut(ORMBaseModel):
    workspace_id: int
    snapshot_id: str
    snapshot_path: str
    source_path: str
    digest: str
    file_count: int
    created_at: str
