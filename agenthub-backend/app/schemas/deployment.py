from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import ORMBaseModel


class DeploymentPortBindingIn(ORMBaseModel):
    host_port: int = Field(ge=1, le=65535)
    container_port: int = Field(ge=1, le=65535)
    protocol: str = Field(default="tcp", pattern="^(tcp|udp)$")


class DeploymentRequest(ORMBaseModel):
    workspace_id: int
    image_ref: str = Field(min_length=1, max_length=255)
    container_name: str = Field(min_length=1, max_length=120)
    sandbox_image: str | None = Field(default=None, max_length=255)
    dockerfile_path: str = Field(default="Dockerfile", min_length=1, max_length=255)
    build_context_path: str = Field(default=".", min_length=1, max_length=255)
    install_command: str | None = None
    test_command: str | None = None
    build_command: str | None = None
    container_command: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    ports: list[DeploymentPortBindingIn] = Field(default_factory=list)


class DeploymentJobOut(ORMBaseModel):
    id: int
    workspace_id: int
    project_id: int
    sandbox_run_id: int | None
    status: str
    target_type: str
    image_ref: str
    container_name: str
    sandbox_image: str
    dockerfile_path: str
    build_context_path: str
    deployed_container_id: str | None
    rollback_image_ref: str | None
    rollback_status: str | None
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
