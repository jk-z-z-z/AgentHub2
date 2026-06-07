from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class GroupAssistantConfigOut(ORMBaseModel):
    group_id: str
    manager_member_id: str | None = None
    enabled: int
    creator_user_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GroupAssistantConfigUpdateRequest(ORMBaseModel):
    enabled: int = Field(default=0, ge=0, le=1)


class GroupTaskNodeIn(ORMBaseModel):
    node_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    detail: str = ""
    role_required: str | None = None
    parent_node_key: str | None = None
    deps: list[str] = Field(default_factory=list)


class GroupTaskRunCreateRequest(ORMBaseModel):
    group_id: str | int
    creator_member_id: str | int
    title: str = Field(min_length=1, max_length=255)
    goal_text: str = Field(min_length=1)
    nodes: list[GroupTaskNodeIn] = Field(default_factory=list)
    trigger_message_id: str | int | None = None


class GroupTaskDagUpdateRequest(ORMBaseModel):
    nodes: list[GroupTaskNodeIn] = Field(default_factory=list)


class GroupTaskRunOut(ORMBaseModel):
    id: str
    group_id: str
    creator_member_id: str
    trigger_message_id: str | None
    title: str
    goal_text: str
    status: str
    created_at: datetime
    updated_at: datetime


class GroupTaskNodeOut(ORMBaseModel):
    id: str
    group_id: str
    run_id: str
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
    manager_review_status: str = "pending"
    manager_review_note: str = ""
    reviewed_at: datetime | None = None
    reviewed_by_member_id: str | None = None
    created_at: datetime
    updated_at: datetime


class GroupTaskGraphOut(ORMBaseModel):
    run_id: str
    nodes: list[GroupTaskNodeOut]
    edges: list[dict]


class GroupTaskEventOut(ORMBaseModel):
    id: str
    message_id: str
    run_id: str | None
    seq: int
    event_type: str
    category: str
    status: str
    payload_json: str
    created_at: datetime
    updated_at: datetime


class GroupTaskNodeMemberRequest(ORMBaseModel):
    member_id: str | int


class GroupTaskNodeCompleteRequest(ORMBaseModel):
    member_id: str | int | None = None
    output_summary: str = ""


class GroupTaskNodeReviewRequest(ORMBaseModel):
    manager_review_status: str = Field(pattern="^(approved|rework)$")
    note: str = ""


class GroupTaskNodeBlockRequest(ORMBaseModel):
    reason: str = Field(min_length=1)
