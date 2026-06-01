from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentInstanceCreateRequest(ORMBaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    base_url: str | None = Field(default=None, max_length=255)
    api_key_ref: str | None = Field(default=None, max_length=255)
    engine_type: str = Field(default="internal_llm", min_length=1, max_length=40)
    engine_config_json: str = Field(default="{}", max_length=200000)
    status: str = Field(default="active", min_length=1, max_length=30)
    template_profile_id: str | int | None = Field(default=None, description="Create-time only: copy from template then detach")
    soul_md: str | None = None


class AgentInstanceOut(ORMBaseModel):
    id: str
    creator_user_id: str
    display_name: str
    description: str | None
    base_url: str | None
    api_key_ref: str | None
    engine_type: str
    engine_config_json: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentInstanceSoulOut(ORMBaseModel):
    soul_md: str


class AgentInstanceSoulUpdateRequest(ORMBaseModel):
    soul_md: str = Field(default="", max_length=200000)
