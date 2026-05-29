from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentProfileCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    description: str | None = None
    system_prompt: str = Field(min_length=1)
    default_model_json: str = "{}"
    planning_mode: str | None = Field(default=None, max_length=50)
    is_active: int = 1


class AgentProfileOut(ORMBaseModel):
    id: int
    name: str
    role: str
    description: str | None
    system_prompt: str
    default_model_json: str
    planning_mode: str | None
    is_active: int
    created_at: datetime
    updated_at: datetime
