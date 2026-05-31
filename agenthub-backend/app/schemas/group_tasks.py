from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class GroupAssistantConfigOut(ORMBaseModel):
    group_id: str
    manager_member_id: str | None
    enabled: int
    creator_user_id: str


class GroupAssistantConfigUpdateRequest(ORMBaseModel):
    enabled: int = Field(default=0, ge=0, le=1)


class GroupTaskNodeIn(ORMBaseModel):
    node_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    detail: str = ""
    role_required: str | None = None
    deps: list[str] = Field(default_factory=list)


class GroupTaskNodeOut(ORMBaseModel):
    id: str
    run_id: str
    node_key: str
    title: str
    detail: str
    role_required: str | None
    deps: list[str]
    status: str
    assignee_kind: str
    assignee_member_id: str | None
    output_summary: str
    manager_review_status: str
    created_at: datetime
    updated_at: datetime


class GroupTaskRunCreateRequest(ORMBaseModel):
    group_id: str | int
    creator_member_id: str | int
    title: str = Field(min_length=1, max_length=255)
    goal_text: str = Field(min_length=1)
    nodes: list[GroupTaskNodeIn] = Field(default_factory=list)
    trigger_message_id: str | int | None = None


class GroupTaskRunOut(ORMBaseModel):
    id: str
    group_id: str
    creator_member_id: str
    trigger_message_id: str | None
    title: str
    goal_text: str
    status: str
    dag_json: str
    runtime_dir: str
    created_at: datetime
    updated_at: datetime


class GroupTaskDagUpdateRequest(ORMBaseModel):
    nodes: list[GroupTaskNodeIn]


class GroupTaskClaimRequest(ORMBaseModel):
    member_id: str | int


class GroupTaskNodeCompleteRequest(ORMBaseModel):
    output_summary: str = Field(min_length=1)


class GroupTaskNodeReviewRequest(ORMBaseModel):
    manager_review_status: str = Field(pattern="^(approved|rework)$")
    note: str = ""


class GroupTaskNodeBlockRequest(ORMBaseModel):
    reason: str = Field(min_length=1)


class GroupTaskEventOut(ORMBaseModel):
    id: str
    run_id: str
    node_id: str | None
    event_type: str
    payload_json: str
    created_at: datetime
    updated_at: datetime
