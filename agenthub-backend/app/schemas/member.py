from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class UserMemberCreateRequest(ORMBaseModel):
    group_id: str
    display_name: str = Field(min_length=1, max_length=120)
    user_ref: str = Field(min_length=1, max_length=120)
    title: str | None = Field(default=None, max_length=120)


class AgentMemberCreateRequest(ORMBaseModel):
    group_id: str
    display_name: str = Field(min_length=1, max_length=120)
    agent_instance_id: str
    title: str | None = Field(default=None, max_length=120)


class MemberUpdateRequest(ORMBaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    title: str | None = Field(default=None, max_length=120)


class MemberOut(ORMBaseModel):
    id: str
    group_id: str
    kind: str
    display_name: str
    user_ref: str | None
    agent_instance_id: str | None
    title: str | None
    created_at: datetime
    updated_at: datetime
