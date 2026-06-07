from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ORMBaseModel


class ExecutionRequest(ORMBaseModel):
    workspace_id: int
    command: str = Field(min_length=1)
    cwd: str = Field(default=".")
    sandbox_image: str | None = Field(default=None, max_length=255)
    network_enabled: bool = False
    env: dict[str, str] = Field(default_factory=dict)


class ExecutionJobOut(ORMBaseModel):
    id: int
    workspace_id: int
    project_id: int
    sandbox_run_id: int | None
    status: str
    job_type: str
    command: str
    cwd: str
    sandbox_image: str
    network_enabled: bool
    attempt_count: int
    stdout: str
    stderr: str
    error_message: str | None
    spec: dict[str, Any]
    context: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
