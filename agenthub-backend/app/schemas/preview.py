from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ORMBaseModel


class PreviewRequest(ORMBaseModel):
    workspace_id: int
    source_path: str = Field(default=".", min_length=1, max_length=255)
    sandbox_image: str | None = Field(default=None, max_length=255)
    install_command: str | None = None
    build_command: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    host_port: int | None = Field(default=None, ge=1, le=65535)


class PreviewJobOut(ORMBaseModel):
    id: int
    workspace_id: int
    project_id: int
    sandbox_run_id: int | None
    status: str
    container_name: str
    container_id: str | None
    sandbox_image: str
    source_path: str
    host_port: int
    preview_root_path: str | None
    url: str | None
    attempt_count: int
    logs_text: str
    error_message: str | None
    spec: dict[str, Any]
    context: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
