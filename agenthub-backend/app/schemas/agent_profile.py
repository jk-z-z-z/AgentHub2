from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentProfileCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    description: str | None = None
    soul_md: str = Field(min_length=1)
    agents_md: str = ""
    profile_md: str = ""
    bootstrap_md: str = ""
    memory_md: str = ""
    heartbeat_md: str = ""
    enabled_files_json: str = "{}"
    model_name: str = Field(default="gpt-4.1-mini", min_length=1, max_length=120)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=None, ge=1, le=200000)
    is_active: int = 1


class AgentProfileOut(ORMBaseModel):
    id: str
    creator_user_id: str
    name: str
    role: str
    description: str | None
    soul_md: str
    agents_md: str
    profile_md: str
    bootstrap_md: str
    memory_md: str
    heartbeat_md: str
    enabled_files_json: str
    model_name: str
    temperature: float
    top_p: float
    max_output_tokens: int | None
    is_active: int
    created_at: datetime
    updated_at: datetime
