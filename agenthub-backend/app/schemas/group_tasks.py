from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class GroupAssistantConfigOut(ORMBaseModel):
    group_id: str
    manager_member_id: str | None
    enabled: int
    creator_user_id: str


class GroupTaskNodeIn(ORMBaseModel):
    node_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    detail: str = ""
    role_required: str | None = None
    parent_node_key: str | None = None
    deps: list[str] = Field(default_factory=list)


class GroupTaskNodeOut(ORMBaseModel):
    id: str
    group_id: str
    parent_node_id: str | None
    parent_node_key: str | None = None
    node_key: str
    title: str
    detail: str
    role_required: str | None
    status: str
    assignee_kind: str
    assignee_member_id: str | None
    attempt: int = 0
    deps: list[str] = Field(default_factory=list)
    input_json: str = "{}"
    result_json: str = "{}"
    error: str = ""
    output_summary: str
    created_at: datetime
    updated_at: datetime


class GroupTaskNodeCreateRequest(ORMBaseModel):
    nodes: list[GroupTaskNodeIn] = Field(default_factory=list)


class GroupTaskNodeMemberRequest(ORMBaseModel):
    member_id: str | int


class GroupTaskNodeCompleteRequest(ORMBaseModel):
    member_id: str | int
    output_summary: str = ""


class GroupTaskNodeFailRequest(ORMBaseModel):
    error: str = ""
