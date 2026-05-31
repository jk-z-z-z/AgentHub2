from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class GroupMemberUserIn(ORMBaseModel):
    user_id: str | int
    display_name: str = Field(min_length=1, max_length=120)
    title: str | None = Field(default=None, max_length=120)


class GroupMemberAgentIn(ORMBaseModel):
    agent_id: str | int
    display_name: str = Field(min_length=1, max_length=120)
    title: str | None = Field(default=None, max_length=120)


class GroupCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    type: str = Field(default="project", pattern="^(project|personal)$")
    users: list[GroupMemberUserIn] = Field(default_factory=list)
    agents: list[GroupMemberAgentIn] = Field(default_factory=list)


class GroupOut(ORMBaseModel):
    id: str
    name: str
    description: str | None
    type: str
    created_at: datetime
    updated_at: datetime
