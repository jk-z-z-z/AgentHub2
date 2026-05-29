from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentInstanceCreateRequest(ORMBaseModel):
    group_id: int
    profile_id: int
    display_name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    base_url: str | None = Field(default=None, max_length=255)
    api_key_ref: str | None = Field(default=None, max_length=255)
    config_json: str = "{}"
    status: str = Field(default="active", min_length=1, max_length=30)


class AgentInstanceOut(ORMBaseModel):
    id: int
    group_id: int
    profile_id: int
    display_name: str
    description: str | None
    base_url: str | None
    api_key_ref: str | None
    config_json: str
    status: str
    created_at: datetime
    updated_at: datetime
